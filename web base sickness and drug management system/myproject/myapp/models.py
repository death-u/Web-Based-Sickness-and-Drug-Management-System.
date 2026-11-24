from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

EXPIRY_WARNING_DAYS = 30


# ---------------------------------------------------------------- roles
class Profile(models.Model):
    ROLES = [("admin", "Admin"), ("doctor", "Doctor"), ("pharmacist", "Pharmacist")]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=12, choices=ROLES, default="doctor")

    def __str__(self):
        return f"{self.user} ({self.get_role_display()})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance, role="admin" if instance.is_superuser else "doctor")


def user_role(user):
    """Superusers are always admins; everyone else uses their profile role."""
    if user.is_superuser:
        return "admin"
    profile = getattr(user, "profile", None)
    return profile.role if profile else "doctor"


# ---------------------------------------------------------------- patients
class Patient(models.Model):
    GENDERS = [("F", "Female"), ("M", "Male"), ("O", "Other")]
    code = models.CharField(max_length=12, unique=True, null=True, blank=True, editable=False)
    full_name = models.CharField(max_length=120)
    gender = models.CharField(max_length=1, choices=GENDERS)
    date_of_birth = models.DateField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=200, blank=True)
    allergies = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"PT-{self.pk:04d}"
            super().save(update_fields=["code"])

    @property
    def age(self):
        today = timezone.localdate()
        d = self.date_of_birth
        return today.year - d.year - ((today.month, today.day) < (d.month, d.day))

    def __str__(self):
        return f"{self.full_name} ({self.code})"


class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visits")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits")
    visit_date = models.DateTimeField(auto_now_add=True)
    symptoms = models.TextField()
    diagnosis = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-visit_date"]

    def __str__(self):
        return f"{self.patient.full_name}: {self.diagnosis}"


# ---------------------------------------------------------------- drugs
class DrugQuerySet(models.QuerySet):
    def expired(self):
        return self.filter(expiry_date__lt=timezone.localdate())

    def expiring(self):
        today = timezone.localdate()
        return self.filter(expiry_date__gte=today, expiry_date__lte=today + timedelta(days=EXPIRY_WARNING_DAYS))

    def restock(self):
        """Low or out of stock."""
        return self.filter(quantity__lte=F("reorder_level"))

    def dispensable(self):
        return self.filter(quantity__gt=0, expiry_date__gte=timezone.localdate())


class Drug(models.Model):
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=60, blank=True)
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10, help_text="Warn when stock falls to this number")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    supplier = models.CharField(max_length=120, blank=True)
    expiry_date = models.DateField()

    objects = DrugQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    @property
    def days_to_expiry(self):
        return (self.expiry_date - timezone.localdate()).days

    @property
    def status_key(self):
        if self.days_to_expiry < 0:
            return "expired"
        if self.quantity == 0:
            return "out"
        if self.quantity <= self.reorder_level:
            return "low"
        if self.days_to_expiry <= EXPIRY_WARNING_DAYS:
            return "expiring"
        return "ok"

    @property
    def status_label(self):
        d = self.days_to_expiry
        return {
            "expired": "Expired",
            "out": "Out of stock",
            "low": "Low stock",
            "expiring": f"Expires in {d} day{'s' if d != 1 else ''}",
            "ok": "In stock",
        }[self.status_key]

    @property
    def badge_class(self):
        return {"expired": "danger", "out": "danger", "low": "warn", "expiring": "warn", "ok": "ok"}[self.status_key]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------- prescriptions
class Prescription(models.Model):
    STATUSES = [("pending", "Pending"), ("dispensed", "Dispensed"), ("cancelled", "Cancelled")]
    visit = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name="prescriptions")
    status = models.CharField(max_length=10, choices=STATUSES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    dispensed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="dispensed")
    dispensed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def patient(self):
        return self.visit.patient

    @property
    def badge_class(self):
        return {"pending": "warn", "dispensed": "ok", "cancelled": "muted"}[self.status]

    @property
    def total(self):
        return sum((i.line_total for i in self.items.select_related("drug")), 0)

    def dispense(self, user):
        """Deduct stock for every item and mark as dispensed. All or nothing."""
        with transaction.atomic():
            rx = Prescription.objects.select_for_update().get(pk=self.pk)
            if rx.status != "pending":
                raise ValueError("This prescription is no longer pending.")
            items = list(rx.items.select_related("drug"))
            if not items:
                raise ValueError("This prescription has no drugs on it.")
            problems = []
            for item in items:
                drug = Drug.objects.select_for_update().get(pk=item.drug_id)
                if drug.days_to_expiry < 0:
                    problems.append(f"{drug.name} is expired")
                elif drug.quantity < item.quantity:
                    problems.append(f"{drug.name}: needs {item.quantity}, only {drug.quantity} in stock")
            if problems:
                raise ValueError("Can't dispense. " + "; ".join(problems) + ".")
            for item in items:
                Drug.objects.filter(pk=item.drug_id).update(quantity=F("quantity") - item.quantity)
            rx.status = "dispensed"
            rx.dispensed_by = user
            rx.dispensed_at = timezone.now()
            rx.save()
        self.refresh_from_db()

    def cancel(self):
        if self.status != "pending":
            raise ValueError("Only pending prescriptions can be cancelled.")
        self.status = "cancelled"
        self.save(update_fields=["status"])

    def __str__(self):
        return f"Prescription #{self.pk}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="items")
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name="prescribed")
    dosage = models.CharField(max_length=160)
    quantity = models.PositiveIntegerField()

    @property
    def stock_after(self):
        return self.drug.quantity - self.quantity

    @property
    def line_total(self):
        return self.drug.unit_price * self.quantity

    @property
    def can_dispense(self):
        return self.drug.days_to_expiry >= 0 and self.drug.quantity >= self.quantity

    def __str__(self):
        return f"{self.drug} x {self.quantity}"