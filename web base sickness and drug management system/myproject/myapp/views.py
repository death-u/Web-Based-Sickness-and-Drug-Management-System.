from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import DrugForm, ItemFormSet, PatientForm, VisitForm
from .models import EXPIRY_WARNING_DAYS, Drug, Patient, Prescription, Visit, user_role


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if user_role(request.user) not in roles:
                messages.error(request, "Your role doesn't have access to that page.")
                return redirect("dashboard")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def page(request, template, section, **ctx):
    ctx.update(role=user_role(request.user), section=section)
    return render(request, template, ctx)


def paginate(request, queryset, per_page=15):
    page_obj = Paginator(queryset, per_page).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return page_obj, params.urlencode()


# ---------------------------------------------------------------- dashboard
@login_required
def index(request):
    today = timezone.localdate()
    soon = today + timedelta(days=EXPIRY_WARNING_DAYS)
    attention = Drug.objects.filter(Q(expiry_date__lte=soon) | Q(quantity__lte=F("reorder_level"))).order_by("expiry_date")
    pending = Prescription.objects.filter(status="pending").select_related("visit__patient", "visit__doctor")
    return page(
        request, "index.html", "dashboard",
        kpi_patients=Patient.objects.count(),
        kpi_visits=Visit.objects.filter(visit_date__date=today).count(),
        kpi_pending=pending.count(),
        kpi_restock=Drug.objects.restock().count(),
        kpi_expired=Drug.objects.expired().count(),
        kpi_expiring=Drug.objects.expiring().count(),
        attention=attention[:6],
        pending=pending[:6],
        recent_visits=Visit.objects.select_related("patient", "doctor")[:6],
    )


# ---------------------------------------------------------------- drugs
@login_required
def drug_list(request):
    q, flt = request.GET.get("q", "").strip(), request.GET.get("filter", "")
    drugs = Drug.objects.all()
    if q:
        drugs = drugs.filter(Q(name__icontains=q) | Q(category__icontains=q) | Q(supplier__icontains=q))
    drugs = {"restock": drugs.restock, "expiring": drugs.expiring, "expired": drugs.expired}.get(flt, lambda: drugs)()
    page_obj, qs = paginate(request, drugs, 20)
    return page(request, "drugs/list.html", "drugs", page_obj=page_obj, qs=qs, q=q, flt=flt)


@role_required("admin", "pharmacist")
def drug_create(request):
    form = DrugForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        drug = form.save()
        messages.success(request, f"{drug.name} added to the inventory.")
        return redirect("drug_list")
    return page(request, "drugs/form.html", "drugs", form=form, title="Add drug")


@role_required("admin", "pharmacist")
def drug_update(request, pk):
    drug = get_object_or_404(Drug, pk=pk)
    form = DrugForm(request.POST or None, instance=drug)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{drug.name} updated.")
        return redirect("drug_list")
    return page(request, "drugs/form.html", "drugs", form=form, title=f"Edit {drug.name}")


@role_required("admin", "pharmacist")
@require_POST
def drug_delete(request, pk):
    drug = get_object_or_404(Drug, pk=pk)
    try:
        drug.delete()
        messages.success(request, f"{drug.name} deleted.")
    except ProtectedError:
        messages.error(request, f"{drug.name} appears on prescriptions, so it can't be deleted. Set its quantity to 0 instead.")
    return redirect("drug_list")


# ---------------------------------------------------------------- patients
@login_required
def patient_list(request):
    q = request.GET.get("q", "").strip()
    patients = Patient.objects.all()
    if q:
        patients = patients.filter(Q(full_name__icontains=q) | Q(code__icontains=q) | Q(phone__icontains=q))
    page_obj, qs = paginate(request, patients)
    return page(request, "patients/list.html", "patients", page_obj=page_obj, qs=qs, q=q)


@role_required("admin", "doctor")
def patient_create(request):
    form = PatientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        patient = form.save()
        messages.success(request, f"{patient.full_name} registered as {patient.code}.")
        return redirect("patient_detail", pk=patient.pk)
    return page(request, "patients/form.html", "patients", form=form, title="Register patient")


@role_required("admin", "doctor")
def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    form = PatientForm(request.POST or None, instance=patient)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Patient details updated.")
        return redirect("patient_detail", pk=patient.pk)
    return page(request, "patients/form.html", "patients", form=form, title=f"Edit {patient.full_name}")


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    visits = patient.visits.select_related("doctor").prefetch_related("prescriptions__items__drug")
    return page(request, "patients/detail.html", "patients", patient=patient, visits=visits)


# ---------------------------------------------------------------- visits
@role_required("admin", "doctor")
def visit_create(request):
    form = VisitForm(request.POST or None, initial={"patient": request.GET.get("patient")})
    formset = ItemFormSet(request.POST or None, instance=Prescription(), prefix="items")
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            visit = form.save(commit=False)
            visit.doctor = request.user
            visit.save()
            if any(f.has_changed() for f in formset.forms):
                rx = Prescription.objects.create(visit=visit)
                formset.instance = rx
                formset.save()
        messages.success(request, f"Visit saved for {visit.patient.full_name}." + (" Prescription sent to the pharmacy." if visit.prescriptions.exists() else ""))
        return redirect("patient_detail", pk=visit.patient_id)
    allergy_map = {p.pk: p.allergies for p in Patient.objects.exclude(allergies="")}
    return page(request, "visits/form.html", "visit", form=form, formset=formset, allergy_map=allergy_map)


# ---------------------------------------------------------------- prescriptions
@login_required
def prescription_list(request):
    status = request.GET.get("status", "")
    rxs = Prescription.objects.select_related("visit__patient", "visit__doctor").prefetch_related("items")
    if status in ("pending", "dispensed", "cancelled"):
        rxs = rxs.filter(status=status)
    page_obj, qs = paginate(request, rxs, 20)
    return page(request, "prescriptions/list.html", "prescriptions", page_obj=page_obj, qs=qs, status=status)


@login_required
def prescription_detail(request, pk):
    rx = get_object_or_404(Prescription.objects.select_related("visit__patient", "visit__doctor", "dispensed_by"), pk=pk)
    items = rx.items.select_related("drug")
    return page(request, "prescriptions/detail.html", "prescriptions", rx=rx, items=items,
                blocked=rx.status == "pending" and not all(i.can_dispense for i in items))


@role_required("admin", "pharmacist")
@require_POST
def prescription_dispense(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)
    try:
        rx.dispense(request.user)
        messages.success(request, f"Prescription #{rx.pk} dispensed. Stock updated.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("prescription_detail", pk=rx.pk)


@role_required("admin", "doctor")
@require_POST
def prescription_cancel(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)
    try:
        rx.cancel()
        messages.success(request, f"Prescription #{rx.pk} cancelled.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("prescription_detail", pk=rx.pk)
