from django.contrib import admin

from .models import AdminUser, Answer, EvaluationTask, GenerationSetting, GenerationTask, Rate, User

DEFAULT_READONLY_FIELDS = [
    "created_at",
    "updated_at",
]


@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "username",
        "last_name",
        "first_name",
        "is_superuser",
        "is_staff",
        "is_active",
        "date_joined",
        "last_login",
    ]

    fields = [
        "email",
        "username",
        "last_name",
        "first_name",
        "is_superuser",
        "is_staff",
        "is_active",
        "date_joined",
        "last_login",
    ]

    readonly_fields = [
        "date_joined",
        "last_login",
    ]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "email",
        "name",
        "role",
        "activated",
        "anonymous",
    ]

    fields = [
        "id",
        "email",
        "name",
        "uid",
        "role",
        "profile_image",
        "activated",
        "anonymous",
        "created_at",
        "updated_at",
    ]

    readonly_fields = [
        "id",
        "uid",
        "anonymous",
        "created_at",
        "updated_at",
    ]


@admin.register(GenerationTask)
class GenerationTaskAdmin(admin.ModelAdmin):
    readonly_fields = DEFAULT_READONLY_FIELDS


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    readonly_fields = DEFAULT_READONLY_FIELDS


@admin.register(EvaluationTask)
class EvaluationTaskAdmin(admin.ModelAdmin):
    readonly_fields = DEFAULT_READONLY_FIELDS


@admin.register(Rate)
class RateAdmin(admin.ModelAdmin):
    readonly_fields = DEFAULT_READONLY_FIELDS


@admin.register(GenerationSetting)
class GenerationSettingAdmin(admin.ModelAdmin):
    readonly_fields = DEFAULT_READONLY_FIELDS
