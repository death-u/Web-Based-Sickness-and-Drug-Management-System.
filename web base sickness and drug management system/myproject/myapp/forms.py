from django import forms
from django.forms import inlineformset_factory

from .models import Drug, Patient, Prescription, PrescriptionItem, Visit


class Styled:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", "input")


DATE = lambda: forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class PatientForm(Styled, forms.ModelForm):
    class Meta:
        model = Patient
        fields = ["full_name", "gender", "date_of_birth", "phone", "address", "allergies"]
        widgets = {
            "date_of_birth": DATE(),
            "allergies": forms.Textarea(attrs={"rows": 3, "placeholder": "e.g. Penicillin, sulfa drugs"}),
        }
        help_texts = {"allergies": "Leave blank if none are known. Doctors and pharmacists see this on every prescription."}


class DrugForm(Styled, forms.ModelForm):
    class Meta:
        model = Drug
        fields = ["name", "category", "quantity", "reorder_level", "unit_price", "supplier", "expiry_date"]
        widgets = {"expiry_date": DATE()}


class PatientChoice(forms.ModelChoiceField):
    def label_from_instance(self, p):
        return f"{p.full_name} ({p.code})"


class VisitForm(Styled, forms.ModelForm):
    patient = PatientChoice(queryset=Patient.objects.all(), empty_label="Select patient")

    class Meta:
        model = Visit
        fields = ["patient", "symptoms", "diagnosis", "notes"]
        widgets = {
            "symptoms": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class DrugChoice(forms.ModelChoiceField):
    def label_from_instance(self, d):
        return f"{d.name} ({d.quantity} in stock)"


class PrescriptionItemForm(Styled, forms.ModelForm):
    drug = DrugChoice(queryset=Drug.objects.none(), empty_label="Select drug")
    quantity = forms.IntegerField(min_value=1, initial=1)

    class Meta:
        model = PrescriptionItem
        fields = ["drug", "dosage", "quantity"]
        widgets = {"dosage": forms.TextInput(attrs={"placeholder": "e.g. 1 tablet twice daily for 5 days"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["drug"].queryset = Drug.objects.dispensable()

    def clean(self):
        data = super().clean()
        drug, qty = data.get("drug"), data.get("quantity")
        if drug and qty and qty > drug.quantity:
            self.add_error("quantity", f"Only {drug.quantity} in stock.")
        return data


ItemFormSet = inlineformset_factory(
    Prescription, PrescriptionItem, form=PrescriptionItemForm, extra=0, can_delete=False
)
