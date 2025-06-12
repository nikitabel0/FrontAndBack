from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Создает суперпользователя с ролью admin'

    def handle(self, *args, **options):
        user = User.objects.create_superuser(
            username='admin',
            email='admin@mail.com',
            password='1'
        )
        user.profile.role = 'admin'
        user.profile.save()
        self.stdout.write(self.style.SUCCESS('Супер-админ создан'))