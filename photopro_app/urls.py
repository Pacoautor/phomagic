from django.contrib import admin
from django.urls import path
from products import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.select_category, name='select_category'),
    path('subcategory/<str:category>/', views.select_subcategory, name='select_subcategory'),
    path('products/<str:category>/<str:subcategory>/', views.view_products, name='view_products'),
]
