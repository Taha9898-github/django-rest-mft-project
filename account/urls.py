from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('obtain-token/', views.ObtainTokenView.as_view(), name='obtain-token'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
]
