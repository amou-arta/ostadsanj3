from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Professor, Review, Question, Answer, UserDailyLimit
from django.contrib import messages

@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'image_preview', 'bio_preview', 'rating_preview')
    search_fields = ('name', 'department', 'bio')
    list_filter = ('department',)
    readonly_fields = ('image_display', 'rating_display')
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('name', 'department', 'image')
        }),
        ('بیوگرافی', {
            'fields': ('bio',),
            'classes': ('wide',),
            'description': 'توضیحاتی درباره سوابق تحصیلی، تخصص‌ها و افتخارات استاد'
        }),
        ('پیش‌نمایش', {
            'fields': ('image_display', 'rating_display'),
            'classes': ('collapse',),
            'description': 'پیش‌نمایش اطلاعات استاد'
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            try:
                return format_html(
                    '<img src="{}" width="50" height="50" style="border-radius:50%;object-fit:cover;border:2px solid #4CAF50;" />',
                    obj.image.url
                )
            except:
                return "🖼️ (خطا در نمایش)"
        return "🖼️ (بدون عکس)"
    
    image_preview.short_description = 'عکس پروفایل'
    
    def bio_preview(self, obj):
        if obj.bio:
            text = obj.bio.replace('\n', ' ').replace('\r', '')
            if len(text) > 60:
                return text[:60] + '...'
            return text
        return '---'
    
    bio_preview.short_description = 'خلاصه بیوگرافی'
    
    def rating_preview(self, obj):
        if hasattr(obj, 'average_rating') and obj.average_rating:
            return f"{obj.average_rating:.1f} ⭐"
        return "بدون امتیاز"
    
    rating_preview.short_description = 'میانگین امتیاز'
    
    def image_display(self, obj):
        if obj.image:
            try:
                return format_html(
                    '<div style="text-align:center;padding:10px;">'
                    '<img src="{}" width="200" height="200" style="border-radius:10px;object-fit:cover;border:3px solid #2196F3;box-shadow:0 4px 8px rgba(0,0,0,0.2);" />'
                    '<p style="margin-top:10px;color:#666;">عکس پروفایل استاد</p>'
                    '</div>',
                    obj.image.url
                )
            except:
                return "<div style='color:red;padding:10px;'>❌ خطا در نمایش عکس</div>"
        return "<div style='color:#888;padding:10px;'>📷 عکس آپلود نشده است</div>"
    
    image_display.short_description = 'پیش‌نمایش عکس'
    
    def rating_display(self, obj):
        if hasattr(obj, 'average_rating') and obj.average_rating:
            rating = obj.average_rating
            full_stars = int(rating)
            half_star = rating - full_stars >= 0.5
            empty_stars = 5 - full_stars - (1 if half_star else 0)
            
            stars = '★' * full_stars + '½' * (1 if half_star else 0) + '☆' * empty_stars
            
            return format_html(
                '<div style="background:#f8f9fa;padding:15px;border-radius:8px;border:1px solid #ddd;">'
                '<h4 style="margin-top:0;color:#333;">امتیاز استاد</h4>'
                '<div style="font-size:24px;color:#FF9800;margin:10px 0;">{} <span style="font-size:18px;color:#666;">({:.1f} از 5)</span></div>'
                '<div style="color:#666;font-size:14px;">بر اساس {} نظر دانشجویان</div>'
                '</div>',
                stars, rating, obj.reviews.filter(is_approved=True).count()
            )
        return "<div style='color:#888;padding:10px;'>⭐ هنوز امتیازی ثبت نشده است</div>"
    
    rating_display.short_description = 'پیش‌نمایش امتیاز'
    
    class Meta:
        verbose_name = 'استاد'
        verbose_name_plural = 'اساتید'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'professor', 'rating_stars', 'is_approved', 'created_at', 'text_preview')
    list_filter = ('is_approved', 'rating')
    search_fields = ('user__username', 'text', 'professor__name')
    list_per_page = 20
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'professor', 'rating')
        }),
        ('متن نظر', {
            'fields': ('text',),
            'classes': ('wide',)
        }),
        ('وضعیت', {
            'fields': ('is_approved',),
            'description': 'نظرات تأیید شده در سایت نمایش داده می‌شوند'
        }),
    )
    
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<div style="color:#FF9800;font-size:16px;">{}</div><small style="color:#666;">({}/5)</small>',
            stars, obj.rating
        )
    
    rating_stars.short_description = 'امتیاز'
    
    def text_preview(self, obj):
        if obj.text:
            text = obj.text.replace('\n', ' ').replace('\r', '')
            if len(text) > 80:
                return text[:80] + '...'
            return text
        return '---'
    
    text_preview.short_description = 'خلاصه نظر'
    
    actions = ['approve_reviews', 'reject_reviews', 'fix_review_counts']
    
    def approve_reviews(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f'✅ {count} نظر تأیید شد.')
    
    approve_reviews.short_description = "تأیید نظرات انتخاب‌شده"
    
    def reject_reviews(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'❌ {count} نظر رد شد.')
    
    reject_reviews.short_description = "رد نظرات انتخاب‌شده"
    
    def fix_review_counts(self, request, queryset):
        """رفع مشکل شمارنده نظرات برای کاربران انتخاب شده"""
        from .models import UserDailyLimit
        from django.utils import timezone
        
        fixed_count = 0
        for review in queryset:
            try:
                limit_date = review.created_at.date()
                daily_limit = UserDailyLimit.objects.filter(
                    user=review.user,
                    date=limit_date
                ).first()
                
                if daily_limit:
                    # شمارش واقعی نظرات در آن تاریخ
                    actual_count = Review.objects.filter(
                        user=review.user,
                        created_at__date=limit_date
                    ).count()
                    
                    if daily_limit.review_count != actual_count:
                        daily_limit.review_count = actual_count
                        daily_limit.save()
                        fixed_count += 1
            except Exception as e:
                self.message_user(request, f'خطا برای نظر {review.id}: {e}', level=messages.ERROR)
        
        self.message_user(request, f'✅ تعداد {fixed_count} رکورد محدودیت اصلاح شد.')
    
    fix_review_counts.short_description = "رفع مشکل شمارنده نظرات"
    
    class Meta:
        verbose_name = 'نظر'
        verbose_name_plural = 'نظرات'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('user', 'professor', 'is_approved', 'created_at', 'text_preview')
    list_filter = ('is_approved',)
    search_fields = ('user__username', 'text', 'professor__name')
    
    fieldsets = (
        ('اطلاعات پرسش', {
            'fields': ('user', 'professor', 'text')
        }),
        ('وضعیت', {
            'fields': ('is_approved',),
            'description': 'پرسش‌های تأیید شده در سایت نمایش داده می‌شوند'
        }),
    )
    
    def text_preview(self, obj):
        if obj.text:
            text = obj.text.replace('\n', ' ').replace('\r', '')
            if len(text) > 80:
                return text[:80] + '...'
            return text
        return '---'
    
    text_preview.short_description = 'متن پرسش'
    
    actions = ['approve_questions', 'reject_questions', 'fix_question_counts']
    
    def approve_questions(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f'✅ {count} پرسش تأیید شد.')
    
    approve_questions.short_description = "تأیید پرسش‌های انتخاب‌شده"
    
    def reject_questions(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'❌ {count} پرسش رد شد.')
    
    reject_questions.short_description = "رد پرسش‌های انتخاب‌شده"
    
    def fix_question_counts(self, request, queryset):
        """رفع مشکل شمارنده پرسش‌ها برای کاربران انتخاب شده"""
        from .models import UserDailyLimit
        
        fixed_count = 0
        for question in queryset:
            try:
                limit_date = question.created_at.date()
                daily_limit = UserDailyLimit.objects.filter(
                    user=question.user,
                    date=limit_date
                ).first()
                
                if daily_limit:
                    # شمارش واقعی پرسش‌ها در آن تاریخ
                    actual_count = Question.objects.filter(
                        user=question.user,
                        created_at__date=limit_date
                    ).count()
                    
                    if daily_limit.question_count != actual_count:
                        daily_limit.question_count = actual_count
                        daily_limit.save()
                        fixed_count += 1
            except Exception as e:
                self.message_user(request, f'خطا برای پرسش {question.id}: {e}', level=messages.ERROR)
        
        self.message_user(request, f'✅ تعداد {fixed_count} رکورد محدودیت اصلاح شد.')
    
    fix_question_counts.short_description = "رفع مشکل شمارنده پرسش‌ها"
    
    class Meta:
        verbose_name = 'پرسش'
        verbose_name_plural = 'پرسش‌ها'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question_preview', 'is_approved', 'created_at', 'text_preview')
    list_filter = ('is_approved',)
    search_fields = ('user__username', 'text', 'question__text')
    
    fieldsets = (
        ('اطلاعات پاسخ', {
            'fields': ('user', 'question', 'text')
        }),
        ('وضعیت', {
            'fields': ('is_approved',),
            'description': 'پاسخ‌های تأیید شده در سایت نمایش داده می‌شوند'
        }),
    )
    
    def question_preview(self, obj):
        if obj.question and obj.question.text:
            text = obj.question.text.replace('\n', ' ').replace('\r', '')
            if len(text) > 60:
                return text[:60] + '...'
            return text
        return '---'
    
    question_preview.short_description = 'پرسش مربوطه'
    
    def text_preview(self, obj):
        if obj.text:
            text = obj.text.replace('\n', ' ').replace('\r', '')
            if len(text) > 80:
                return text[:80] + '...'
            return text
        return '---'
    
    text_preview.short_description = 'متن پاسخ'
    
    actions = ['approve_answers', 'reject_answers']
    
    def approve_answers(self, request, queryset):
        count = queryset.update(is_approved=True)
        self.message_user(request, f'✅ {count} پاسخ تأیید شد.')
    
    approve_answers.short_description = "تأیید پاسخ‌های انتخاب‌شده"
    
    def reject_answers(self, request, queryset):
        count = queryset.update(is_approved=False)
        self.message_user(request, f'❌ {count} پاسخ رد شد.')
    
    reject_answers.short_description = "رد پاسخ‌های انتخاب‌شده"
    
    class Meta:
        verbose_name = 'پاسخ'
        verbose_name_plural = 'پاسخ‌ها'


@admin.register(UserDailyLimit)
class UserDailyLimitAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'review_count', 'question_count', 'can_post_review_display', 'can_post_question_display')
    list_filter = ('date',)
    search_fields = ('user__username',)
    readonly_fields = ('user', 'date')
    
    def can_post_review_display(self, obj):
        if obj.can_post_review:
            return format_html('<span style="color:green;">✓ بله ({} باقی‌مانده)</span>', 4 - obj.review_count)
        return format_html('<span style="color:red;">✗ خیر (به حد مجاز رسیده)</span>')
    
    can_post_review_display.short_description = 'می‌تواند نظر بدهد'
    
    def can_post_question_display(self, obj):
        if obj.can_post_question:
            return format_html('<span style="color:green;">✓ بله ({} باقی‌مانده)</span>', 4 - obj.question_count)
        return format_html('<span style="color:red;">✗ خیر (به حد مجاز رسیده)</span>')
    
    can_post_question_display.short_description = 'می‌تواند پرسش بدهد'
    
    actions = ['recalculate_counts']
    
    def recalculate_counts(self, request, queryset):
        """محاسبه مجدد شمارنده‌ها بر اساس داده‌های واقعی"""
        from django.db.models import Count
        
        for daily_limit in queryset:
            # شمارش واقعی نظرات
            actual_review_count = Review.objects.filter(
                user=daily_limit.user,
                created_at__date=daily_limit.date
            ).count()
            
            # شمارش واقعی پرسش‌ها
            actual_question_count = Question.objects.filter(
                user=daily_limit.user,
                created_at__date=daily_limit.date
            ).count()
            
            daily_limit.review_count = actual_review_count
            daily_limit.question_count = actual_question_count
            daily_limit.save()
        
        self.message_user(request, f'✅ شمارنده‌های {queryset.count()} رکورد محاسبه مجدد شد.')
    
    recalculate_counts.short_description = "محاسبه مجدد شمارنده‌ها"


# تنظیمات سرتیتر پنل ادمین
admin.site.site_header = 'پنل مدیریت سامانه ارزشیابی اساتید'
admin.site.site_title = 'سامانه ارزشیابی اساتید'
admin.site.index_title = 'خوش آمدید به پنل مدیریت'