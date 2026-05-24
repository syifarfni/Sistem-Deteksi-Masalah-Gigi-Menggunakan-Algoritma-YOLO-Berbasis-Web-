from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect
from django.contrib.auth.models import User

# =================== LOGIN ===================
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        next_url = request.POST.get('next') or '/'  # redirect ke next (misal /detect/)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url)
        else:
            messages.error(request, 'Username atau password salah.')

    return render(request, 'login.html')


# =================== LOGOUT ===================
def logout_view(request):
    logout(request)
    return redirect('login')  # balik ke login page setelah logout


# =================== REGISTER ===================
def register_view(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Validate form data
        errors = []
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            errors.append('Username sudah digunakan.')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            errors.append('Email sudah digunakan.')
            
        # Check if passwords match
        if password1 != password2:
            errors.append('Password tidak cocok.')
            
        # Check password length
        if len(password1) < 8:
            errors.append('Password harus minimal 8 karakter.')
            
        # If there are no errors, create the user
        if not errors:
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1
                )
                
                # Log the user in automatically
                login(request, user)
                
                # Send success message
                messages.success(request, 'Registrasi berhasil. Selamat datang di DentScan!')
                
                # Redirect to home page
                return redirect('home')
            except Exception as e:
                # If there's an error creating the user
                messages.error(request, f'Terjadi kesalahan: {str(e)}')
        else:
            # Display the errors
            for error in errors:
                messages.error(request, error)
    
    # If method is GET or form validation failed, render the registration page
    return render(request, 'register.html')


#  =================== pass ===================
def ganti_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Supaya gak logout otomatis
            messages.success(request, 'Password berhasil diganti.')
            return redirect('profile')  
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = PasswordChangeForm(user=request.user)
    return render(request, 'accounts/ganti_pass.html', {'form': form})

# =================== PROFILE ===================
@login_required
def profile_view(request):
    return render(request, 'profile.html')