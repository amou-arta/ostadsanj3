from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Review, Question, Answer, Professor, ProfessorEvaluation
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
import random
import operator

class ChallengeMixin:
    """میکسین برای اضافه کردن چالش امنیتی به فرم‌ها - فقط سوالات ریاضی"""
    
    # فقط سوالات ریاضی
    MATH_CHALLENGES = [
        {
            'question': 'حاصل جمع ۵ و ۳ چیست؟',
            'answer': '8',
            'operation': (5, 3, operator.add, 'جمع'),
            'hint': 'فقط عدد وارد کنید'
        },
        {
            'question': 'حاصل ضرب ۴ در ۶ چیست؟',
            'answer': '24',
            'operation': (4, 6, operator.mul, 'ضرب'),
            'hint': 'فقط عدد وارد کنید'
        },
        {
            'question': 'حاصل تفریق ۱۲ منهای ۷ چیست؟',
            'answer': '5',
            'operation': (12, 7, operator.sub, 'تفریق'),
            'hint': 'فقط عدد وارد کنید'
        },
        {
            'question': 'حاصل ۱۵ تقسیم بر ۳ چیست؟',
            'answer': '5',
            'operation': (15, 3, operator.truediv, 'تقسیم'),
            'hint': 'فقط عدد وارد کنید'
        },
        {
            'question': 'حاصل ۸ به علاوه ۹ چیست؟',
            'answer': '17',
            'operation': (8, 9, operator.add, 'جمع'),
            'hint': 'فقط عدد وارد کنید'
        },
        {
            'question': 'حاصل ۷ ضربدر ۸ چیست؟',
            'answer': '56',
            'operation': (7, 8, operator.mul, 'ضرب'),
            'hint': 'فقط عدد وارد کنید'
        },
        {
            'question': 'حاصل ۲۰ منهای ۱۳ چیست؟',
            'answer': '7',
            'operation': (20, 13, operator.sub, 'تفریق'),
            'hint': 'فقد عدد وارد کنید'
        },
        {
            'question': 'حاصل ۱۸ تقسیم بر ۲ چیست؟',
            'answer': '9',
            'operation': (18, 2, operator.truediv, 'تقسیم'),
            'hint': 'فقط عدد وارد کنید'
        },
        {
            'question': 'حاصل ۱۰ به علاوه ۱۵ چیست؟',
            'answer': '25',
            'operation': (10, 15, operator.add, 'جمع'),
            'hint': 'فقط عدد وارد کنید'
        },
        {
            'question': 'حاصل ۶ ضربدر ۷ چیست؟',
            'answer': '42',
            'operation': (6, 7, operator.mul, 'ضرب'),
            'hint': 'فقط عدد وارد کنید'
        },
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # اگر فرم POST شده، سوال را از داده‌های ورودی بخوان
        if 'challenge_question' in self.data and self.data['challenge_question']:
            # پیدا کردن سوال بر اساس متن ذخیره شده در فیلد hidden
            challenge_text = self.data['challenge_question']
            self.challenge_data = None
            
            for challenge in self.MATH_CHALLENGES:
                if challenge['question'] == challenge_text:
                    self.challenge_data = challenge
                    break
            
            # اگر سوال پیدا نشد، یک سوال جدید انتخاب کن
            if not self.challenge_data:
                self.challenge_data = random.choice(self.MATH_CHALLENGES)
        else:
            # برای فرم GET، یک سوال تصادفی انتخاب کن
            self.challenge_data = random.choice(self.MATH_CHALLENGES)
        
        # اضافه کردن فیلد چالش - با مقدار از پیش تعیین شده
        self.fields['challenge_question'] = forms.CharField(
            initial=self.challenge_data['question'],
            widget=forms.HiddenInput(attrs={'value': self.challenge_data['question']}),
            required=False
        )
        
        self.fields['challenge_answer'] = forms.CharField(
            label=_('پاسخ به سوال ریاضی'),
            help_text=self.challenge_data['hint'],
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'فقط عدد وارد کنید'
            }),
            required=True
        )
    
    def get_challenge_question(self):
        """متد برای دریافت سوال چالش برای نمایش در template"""
        return self.challenge_data['question']
    
    def clean(self):
        """بررسی پاسخ چالش ریاضی - در clean برای دسترسی به همه فیلدها"""
        cleaned_data = super().clean()
        
        # دریافت سوال از فیلد hidden
        challenge_question = cleaned_data.get('challenge_question')
        user_answer = cleaned_data.get('challenge_answer', '').strip()
        
        if not challenge_question:
            raise forms.ValidationError(
                _('خطا در بارگذاری سوال امنیتی. لطفاً صفحه را رفرش کنید.'),
                code='challenge_missing'
            )
        
        # پیدا کردن پاسخ صحیح بر اساس سوال
        correct_answer = None
        for challenge in self.MATH_CHALLENGES:
            if challenge['question'] == challenge_question:
                correct_answer = challenge['answer']
                break
        
        if not correct_answer:
            raise forms.ValidationError(
                _('خطا در اعتبارسنجی سوال امنیتی. لطفاً صفحه را رفرش کنید.'),
                code='challenge_invalid'
            )
        
        if not user_answer:
            self.add_error('challenge_answer', 
                _('لطفاً پاسخ سوال ریاضی را وارد کنید.'),
            )
            return cleaned_data
        
        try:
            # تبدیل پاسخ کاربر به عدد
            user_num = int(user_answer)
            correct_num = int(correct_answer)
            
            if user_num != correct_num:
                self.add_error('challenge_answer',
                    _('پاسخ سوال ریاضی نادرست است.'),
                )
        except ValueError:
            # اگر کاربر عدد وارد نکرده
            if user_answer != correct_answer:
                self.add_error('challenge_answer',
                    _('پاسخ باید عدد باشد. پاسخ صحیح: {}').format(correct_answer),
                )
        
        return cleaned_data


class SignUpForm(ChallengeMixin, UserCreationForm):
    """فرم ثبت‌نام با چالش ریاضی"""
    
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']
        labels = {
            'username': _('نام کاربری'),
            'password1': _('رمز عبور'),
            'password2': _('تکرار رمز عبور'),
        }
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'یک نام کاربری انتخاب کنید'
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'رمز عبور خود را وارد کنید'
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'رمز عبور خود را تکرار کنید'
            }),
        }


class LoginForm(ChallengeMixin, AuthenticationForm):
    """فرم ورود با چالش ریاضی"""
    
    username = forms.CharField(
        label=_('نام کاربری'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام کاربری خود را وارد کنید'
        })
    )
    
    password = forms.CharField(
        label=_('رمز عبور'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور خود را وارد کنید'
        })
    )
    
    class Meta:
        fields = ['username', 'password']


class ReviewForm(forms.ModelForm):
    """فرم نظر"""
    
    class Meta:
        model = Review
        fields = ['text', 'rating']
        labels = {
            'text': _('متن نظر'),
            'rating': _('امتیاز'),
        }
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'نظر خود را درباره این استاد بنویسید...',
                'minlength': '20',
                'maxlength': '2000'
            }),
            'rating': forms.Select(
                choices=[(i, f'{i} ستاره') for i in range(1, 6)],
                attrs={'class': 'form-select'}
            )
        }


class QuestionForm(forms.ModelForm):
    """فرم پرسش"""
    
    class Meta:
        model = Question
        fields = ['text']
        labels = {
            'text': _('متن پرسش'),
        }
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'پرسش خود را درباره این استاد مطرح کنید...',
                'minlength': '10',
                'maxlength': '1000'
            })
        }


class AnswerForm(forms.ModelForm):
    """فرم پاسخ"""
    
    class Meta:
        model = Answer
        fields = ['text']
        labels = {
            'text': _('متن پاسخ'),
        }
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'پاسخ خود را بنویسید...',
                'minlength': '10',
                'maxlength': '1000'
            })
        }


class ProfessorEvaluationForm(forms.ModelForm):
    """فرم ارزیابی کیفی استاد"""
    
    class Meta:
        model = ProfessorEvaluation
        fields = [
            'teaching_method',
            'grading_flexibility',
            'exam_difficulty',
            'subject_knowledge',
            'respect',
            'student_interaction'
        ]
        labels = {
            'teaching_method': _('روش تدریس'),
            'grading_flexibility': _('انعطاف پذیری در نمره دهی'),
            'exam_difficulty': _('سختی امتحانات'),
            'subject_knowledge': _('سواد در درس مربوطه'),
            'respect': _('ادب و احترام'),
            'student_interaction': _('تعامل با دانشجو'),
        }
        widgets = {
            'teaching_method': forms.Select(
                choices=[(i, f'{i} ستاره') for i in range(1, 6)],
                attrs={'class': 'form-select star-rating'}
            ),
            'grading_flexibility': forms.Select(
                choices=[(i, f'{i} ستاره') for i in range(1, 6)],
                attrs={'class': 'form-select star-rating'}
            ),
            'exam_difficulty': forms.Select(
                choices=[(i, f'{i} ستاره') for i in range(1, 6)],
                attrs={'class': 'form-select star-rating'}
            ),
            'subject_knowledge': forms.Select(
                choices=[(i, f'{i} ستاره') for i in range(1, 6)],
                attrs={'class': 'form-select star-rating'}
            ),
            'respect': forms.Select(
                choices=[(i, f'{i} ستاره') for i in range(1, 6)],
                attrs={'class': 'form-select star-rating'}
            ),
            'student_interaction': forms.Select(
                choices=[(i, f'{i} ستاره') for i in range(1, 6)],
                attrs={'class': 'form-select star-rating'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تنظیم پیش‌فرض 3 ستاره برای همه فیلدها
        for field_name in self.fields:
            self.fields[field_name].initial = 3


class ProfessorSearchForm(forms.Form):
    query = forms.CharField(
        max_length=200,
        required=False,
        label='جستجوی استاد',
        widget=forms.TextInput(attrs={
            'placeholder': 'نام یا دپارتمان استاد را وارد کنید',
            'class': 'form-control'
        })
    )


class ProfessorAdminForm(forms.ModelForm):
    class Meta:
        model = Professor
        fields = ['name', 'department', 'bio', 'image']
        labels = {
            'name': _('نام کامل'),
            'department': _('دانشکده/دپارتمان'),
            'bio': _('بیوگرافی'),
            'image': _('عکس پروفایل'),
        }
        widgets = {
            'bio': forms.Textarea(attrs={
                'rows': 5, 
                'class': 'vLargeTextField',
                'placeholder': 'توضیحاتی درباره سوابق تحصیلی، تخصص‌ها و افتخارات استاد...'
            }),
            'name': forms.TextInput(attrs={
                'class': 'vTextField',
                'placeholder': 'نام و نام خانوادگی استاد'
            }),
            'department': forms.TextInput(attrs={
                'class': 'vTextField',
                'placeholder': 'مثال: مهندسی کامپیوتر'
            }),
        }