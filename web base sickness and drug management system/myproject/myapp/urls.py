from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("drugs/", views.drug_list, name="drug_list"),
    path("drugs/new/", views.drug_create, name="drug_create"),
    path("drugs/<int:pk>/edit/", views.drug_update, name="drug_update"),
    path("drugs/<int:pk>/delete/", views.drug_delete, name="drug_delete"),

    path("patients/", views.patient_list, name="patient_list"),
    path("patients/new/", views.patient_create, name="patient_create"),
    path("patients/<int:pk>/", views.patient_detail, name="patient_detail"),
    path("patients/<int:pk>/edit/", views.patient_update, name="patient_update"),

    path("visits/new/", views.visit_create, name="visit_create"),

    path("prescriptions/", views.prescription_list, name="prescription_list"),
    path("prescriptions/<int:pk>/", views.prescription_detail, name="prescription_detail"),
    path("prescriptions/<int:pk>/dispense/", views.prescription_dispense, name="prescription_dispense"),
    path("prescriptions/<int:pk>/cancel/", views.prescription_cancel, name="prescription_cancel"),
]
