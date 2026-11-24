from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Drug, Patient, Prescription, PrescriptionItem, Profile, Visit

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class RoleUserAdmin(UserAdmin):
    inlines = [ProfileInline]

    def get_inline_instances(self, request, obj=None):
        if obj is None:  # "Add user" page: the signal already creates the Profile
            return []
        return super().get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, RoleUserAdmin)


class ItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0


@admin.register(Drug)
class DrugAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "quantity", "reorder_level", "expiry_date")
    search_fields = ("name", "category", "supplier")


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "gender", "phone")
    search_fields = ("full_name", "code", "phone")


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("patient", "diagnosis", "doctor", "visit_date")


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "visit", "status", "created_at")
    inlines = [ItemInline]