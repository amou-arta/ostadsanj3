from django.core.management.base import BaseCommand
from reviews.models import fix_current_daily_limits

class Command(BaseCommand):
    help = 'رفع مشکل محدودیت‌های روزانه کاربران با تطبیق شمارنده‌ها با داده‌های واقعی'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('در حال رفع مشکل محدودیت‌های روزانه...'))
        
        fix_current_daily_limits()
        
        self.stdout.write(self.style.SUCCESS('✓ رفع مشکل محدودیت‌های روزانه با موفقیت انجام شد.'))
        self.stdout.write('از این به بعد وقتی نظر یا پرسشی حذف می‌شود، شمارنده به طور خودکار کاهش می‌یابد.')