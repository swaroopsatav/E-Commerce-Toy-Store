from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from import_export.admin import ImportExportModelAdmin
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from .models import Category, Product, ProductImage, CategoryImage
from django.db.models import Count
from django.db.models import Sum, F
from django_filters import FilterSet, MultipleChoiceFilter

class CategoryFilter(FilterSet):
    category = MultipleChoiceFilter(
        field_name='categories__name',
        choices=Category.objects.values_list('name', 'name'),
        label=_('Category'),
        lookup_expr='exact'
    )

    class Meta:
        model = Product
        fields = ['category']

class StockStatusFilter(FilterSet):
    stock_status = MultipleChoiceFilter(
        choices=[
            ('in_stock', _('In Stock')),
            ('out_of_stock', _('Out of Stock')),
            ('low_stock', _('Low Stock'))
        ],
        label=_('Stock Status'),
        method='filter_stock_status'
    )

    class Meta:
        model = Product
        fields = ['stock_status']

    def filter_stock_status(self, queryset, name, value):
        if 'in_stock' in value:
            queryset = queryset.filter(stock__gt=0)
        if 'out_of_stock' in value:
            queryset = queryset.filter(stock=0)
        if 'low_stock' in value:
            queryset = queryset.filter(stock__gt=0, stock__lte=10)
        return queryset

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'image_preview')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height: 50px; border-radius: 5px;"/>',
                obj.image.url
            )
        return "-"
    
    image_preview.short_description = "Preview"

class CategoryImageInline(admin.TabularInline):
    model = CategoryImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'image_preview')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height: 50px; border-radius: 5px;"/>',
                obj.image.url
            )
        return "-"
    
    image_preview.short_description = "Preview"

class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        fields = (
            'id', 'name', 'slug', 'parent', 'description', 'is_active',
            'created_at', 'updated_at'
        )
        export_order = fields

class ProductResource(resources.ModelResource):
    categories = fields.Field(
        column_name='categories',
        attribute='categories',
        widget=ManyToManyWidget(Category, field='name', separator='|')
    )

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'description', 'price', 'discount_price',
            'stock', 'is_active', 'is_featured', 'created_at', 'updated_at',
            'categories'
        )
        export_order = fields

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = (
        'id', 'name', 'slug', 'category_list', 'final_price', 'stock_status',
        'is_active', 'is_featured', 'created_at', 'updated_at', 'image_preview'
    )
    list_filter = (
        'is_active', 'is_featured', 'created_at', 'updated_at',
        'categories__name', 'stock', 'price', 'discount_price'
    )
    search_fields = (
        'name', 'description', 'slug', 'categories__name',
        'categories__description'
    )
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)
    inlines = [ProductImageInline]
    readonly_fields = (
        'image_preview', 'created_at', 'updated_at', 'final_price',
        'total_orders', 'total_revenue'
    )
    
    fieldsets = (
        (_('Product Details'), {
            'fields': (
                'name', 'slug', 'description', 'price', 'discount_price',
                'stock', 'is_active', 'is_featured', 'categories'
            )
        }),
        (_('Images'), {
            'fields': ('image_preview', 'images')
        }),
        (_('Analytics'), {
            'fields': ('total_orders', 'total_revenue')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'categories', 'images'
        ).annotate(
            total_orders=Count('order_items__order', distinct=True)
        )

    def category_list(self, obj):
        return ", ".join([cat.name for cat in obj.categories.all()])
    category_list.short_description = _('Categories')

    def final_price(self, obj):
        return obj.final_price
    final_price.short_description = _('Price')

    def stock_status(self, obj):
        if obj.stock <= 0:
            color = 'danger'
            status = _('Out of Stock')
        elif obj.stock <= 5:
            color = 'warning'
            status = _('Low Stock')
        else:
            color = 'success'
            status = _('In Stock')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, status
        )
    stock_status.short_description = _('Stock Status')
    stock_status.allow_tags = True

    def image_preview(self, obj):
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image and primary_image.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" alt="{}">',
                primary_image.image.url,
                primary_image.alt_text or 'Product Image'
            )
        return "-"
    image_preview.short_description = _('Image')

    def total_orders(self, obj):
        return getattr(obj, 'total_orders', 0)
    total_orders.short_description = _('Total Orders')
    total_orders.admin_order_field = 'total_orders'

    def total_revenue(self, obj):
        total = obj.order_items.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total'] or 0
        return f"₹{total:.2f}"
    total_revenue.short_description = _('Total Revenue')

    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'Successfully activated {updated} products.'
        )
    make_active.short_description = _('Mark selected products as active')

    def make_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'Successfully deactivated {updated} products.'
        )
    make_inactive.short_description = _('Mark selected products as inactive')

    actions = [make_active, make_inactive]

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'parent', 'is_active', 'product_count', 'created_at', 'updated_at',
        'image_preview'
    )
    list_filter = (
        'parent', 'is_active', 'created_at', 'updated_at'
    )
    search_fields = (
        'name', 'slug', 'description', 'parent__name'
    )
    prepopulated_fields = {
        'slug': ('name',)
    }
    ordering = ('name',)
    readonly_fields = (
        'created_at', 'updated_at', 'product_count', 'image_preview'
    )
    fieldsets = (
        (_('Category Details'), {
            'fields': (
                'name', 'slug', 'parent', 'description', 'image', 'image_preview', 'is_active'
            )
        }),
        (_('Metadata'), {
            'fields': (
                'created_at', 'updated_at', 'product_count'
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            product_count=Count('products', distinct=True)
        )

    def product_count(self, obj):
        return obj.product_count
    product_count.short_description = _('Product Count')
    product_count.admin_order_field = 'product_count'

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" alt="{}">',
                obj.image.url,
                obj.alt_text or 'Category Image'
            )
        return "-"
    image_preview.short_description = _('Image Preview')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'parent':
            kwargs['queryset'] = Category.objects.exclude(id__in=Category.objects.filter(parent__isnull=False).values('id'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.parent and obj.parent.parent:
            obj.parent = obj.parent.parent
            obj.save()
        if not obj.slug:
            obj.slug = slugify(obj.name)
            # Ensure slug uniqueness
            base_slug = obj.slug
            counter = 1
            while Category.objects.filter(slug=obj.slug).exclude(id=obj.id).exists():
                obj.slug = f"{base_slug}-{counter}"
                counter += 1
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            logger.error(f"Error saving category: {str(e)}")
            raise

    def get_form(self, request, obj=None, **kwargs):
        try:
            form = super().get_form(request, obj, **kwargs)
            if 'parent' in form.base_fields:
                qs = Category.objects.exclude(id=obj.id if obj else None)
                # Exclude all descendants
                if obj:
                    descendants = obj.get_descendants()
                    qs = qs.exclude(id__in=[cat.id for cat in descendants])
                form.base_fields['parent'].queryset = qs.filter(is_active=True)
            return form
        except Exception as e:
            logger.error(f"Error in get_form: {str(e)}")
            return super().get_form(request, obj, **kwargs)

# Remove this duplicate ProductAdmin class since we already have one defined earlier
# The original ProductAdmin class with resource_class and other configurations is better
# This class is causing the AlreadyRegistered error
# pass
            return super().get_queryset(request).prefetch_related('categories', 'images')
        except Exception as e:
            logger.error(f"Error in get_queryset: {str(e)}")
            return super().get_queryset(request)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "categories":
            try:
                kwargs["queryset"] = Category.objects.filter(is_active=True)
            except Exception as e:
                logger.error(f"Error getting categories: {str(e)}")
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    class Media:
        css = {
            'all': (
                'admin/css/custom.css',
            )
        }
        js = (
            'admin/js/custom.js',
        )
