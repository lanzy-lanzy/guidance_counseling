from django.contrib.auth import get_user_model
User = get_user_model()

# Delete existing admin user if it exists
User.objects.filter(username='admin').delete()

# Create new admin user
admin_user = User.objects.create_user(
    username='admin',
    email='admin@example.com',
    password='admin123',
    role='admin',
    is_active=True,
    is_staff=True,
    is_superuser=True,
    approval_status='approved'
)
print("Admin user created successfully")
