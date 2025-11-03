from django.contrib import admin
from django.urls import path
from products import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.select_category, name='select_category'),
    path('subcategory/<str:category_name>/', views.select_subcategory, name='select_subcategory'),
    path('view/<str:category_name>/<str:subcategory_name>/', views.select_view, name='select_view'),
]
