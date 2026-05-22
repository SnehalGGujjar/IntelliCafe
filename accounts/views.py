from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetConfirmView,
    PasswordResetDoneView, PasswordResetCompleteView
)
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
import random
import datetime

OTP_EXPIRY_MINUTES = 10


def login_view(request):
    if request.user.is_authenticated:
        return redirect('admin:index' if request.user.is_staff else 'menu:today')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff:
                # Staff + employees require OTP
                code = f"{random.randint(100000, 999999)}"
                request.session['otp_user_id'] = user.id
                request.session['otp_code'] = code
                request.session['otp_created_at'] = timezone.now().isoformat()
                send_mail(
                    subject='Your CafeBrew OTP Code',
                    message=f'Your OTP code is: {code}\n\nThis code expires in {OTP_EXPIRY_MINUTES} minutes.',
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@example.com'),
                    recipient_list=[user.email] if user.email else [],
                    fail_silently=True,
                )
                return redirect('accounts:otp')
            else:
                # Regular customers log in and go to menu
                login(request, user)
                return redirect('menu:today')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')


def otp_view(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip()
        stored_code = request.session.get('otp_code')
        created_at_str = request.session.get('otp_created_at')

        # Check OTP expiry
        if created_at_str:
            created_at = datetime.datetime.fromisoformat(created_at_str)
            # Make timezone-aware if needed
            if timezone.is_naive(created_at):
                created_at = timezone.make_aware(created_at)
            elapsed = (timezone.now() - created_at).total_seconds() / 60
            if elapsed > OTP_EXPIRY_MINUTES:
                for k in ('otp_code', 'otp_user_id', 'otp_created_at'):
                    request.session.pop(k, None)
                messages.error(request, f'OTP expired. Please log in again.')
                return redirect('accounts:login')

        if code and code == stored_code:
            User = get_user_model()
            try:
                user = User.objects.get(id=request.session.get('otp_user_id'))
            except User.DoesNotExist:
                messages.error(request, 'Session expired. Please log in again.')
                return redirect('accounts:login')
            login(request, user)
            for k in ('otp_code', 'otp_user_id', 'otp_created_at'):
                request.session.pop(k, None)
            return redirect('admin:index')
        messages.error(request, 'Invalid OTP. Please try again.')
    return render(request, 'accounts/otp.html')


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password changed successfully.')
            return redirect('admin:index')
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


class ForgotPasswordView(PasswordResetView):
    template_name = 'accounts/forgot.html'
    email_template_name = 'accounts/forgot_email.txt'
    success_url = reverse_lazy('accounts:forgot_done')


class ForgotPasswordDoneView(PasswordResetDoneView):
    template_name = 'accounts/forgot_done.html'


class ForgotPasswordConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/forgot_confirm.html'
    success_url = reverse_lazy('accounts:forgot_complete')


class ForgotPasswordCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/forgot_complete.html'
