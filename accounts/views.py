   
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlparse
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError, RestrictedError
from .models import User
from .serializers import *
from rest_framework.permissions import AllowAny
from django.template.loader import render_to_string
from django.contrib.auth.hashers import make_password
from rest_framework.pagination import PageNumberPagination
from datetime import date 
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
import random
from threading import Timer
from datetime import timedelta
from .utils import *
from rest_framework.views import APIView
from django.contrib.auth.hashers import make_password
from .permissions import *




class TenPagePagination(PageNumberPagination):
    page_size = 10 # Number of items per page
    page_size_query_param = 'page_size'  # Optional: allow client to set page size
    max_page_size = 50  # Optional: upper limit on page size

    def get_paginated_response(self, data):
        return Response({
            'page': self.page.number,
            'pages': self.page.paginator.num_pages,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
        })
class UserRegistrationView(generics.CreateAPIView):
    permission_classes = [] 
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        required_fields = ['email', 'password']

        for field in required_fields:
            if field not in request.data:
                raise ValidationError({field: ["This field is required."]})

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp = generate_otp()
        user.otp_secret = otp
        user.otp_created_at = timezone.now()
        user.save()

        Timer(60.0, clear_otp, [user]).start()

        html_content = render_to_string('confirmation_mail.html', {
       
            'otp': otp,
            'domain': settings.FRONTEND_BASE_URL,
        })

      
        send_email(user.email, "KEN OTP Confirmation", html_content)
        token = generate_jwt_token(user)
        print(token)


        return Response({
            'token': token,
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)



class LoginApiView(generics.GenericAPIView):
    serializer_class=LoginSerializer
    permission_classes = [AllowAny] 
   
    def post(self,request,*args,**kwargs):
     serializer = self.get_serializer(data=request.data)
     serializer.is_valid(raise_exception=True)
     user=serializer.validated_data['user']
     token=generate_jwt_token(user)
     return Response(
                {
                    "token":token,
                    "id":user.id,
                    "role":user.role,
                    "email":user.email,
                    "full_name":user.full_name,
                    "avatar":user.avatar.url if user.avatar else None
                },status=status.HTTP_200_OK)
       

# class ResendOTPView(APIView):
#     permission_classes = [AllowAny]

    

#     def post(self, request):
#         email = request.data['email']  
#         is_email= self.request.query_params.get("change_email", None)
        
#         print(is_email)
#         if is_email :
#          print("kk")
#          try:
#             user = User.objects.get(email_temp=email)
#          except User.DoesNotExist:
#             return Response({"error": "no email to be changed is here ."}, status=status.HTTP_404_NOT_FOUND)

#          otp = generate_otp()
#          user.otp_secret = otp
#          user.otp_created_at = timezone.now()
#          user.save()
#          Timer(60.0, clear_otp, [user]).start()

      
#          html_content = render_to_string('confirmation_mail.html', {
#             'user': user,
#             'otp': otp,
#             'domain': 'localhost:8000'
#         })

      
#          send_email(user.email, "OTP Resend Confirmation", html_content)

#          return Response({"message": "OTP has been resent."}, status=status.HTTP_200_OK)

#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist:
#             return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
       
#         otp = generate_otp()
#         user.otp_secret = otp
#         user.otp_created_at = timezone.now()
#         user.save()
        
      
#         Timer(60.0, clear_otp, [user]).start()

      
#         html_content = render_to_string('confirmation_mail.html', {
#             'user': user,
#             'otp': otp,
#             'domain': 'localhost:8000'
#         })

      
#         send_email(user.email, "OTP Resend Confirmation", html_content)

#         return Response({"message": "OTP has been resent."}, status=status.HTTP_200_OK)
class ResendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email:
            return Response(
                {"email": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Only treat as change_email when explicitly "true"; "false" or missing => resend to main email
        change_email = request.query_params.get("change_email", "").strip().lower() == "true"
        target_field = "email_temp" if change_email else "email"

        user = User.objects.filter(**{target_field: email}).first()

        if not user:
            return Response(
                {"error": f"No user found with {target_field.replace('_', ' ')} = {email}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        self._issue_otp(change_email, user)
        sent = self._send_otp_email(change_email, user)
        if not sent:
            return Response(
                {
                    "error": "Email could not be sent. Please check the address or try again later.",
                    "code": "email_send_failed",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"message": "OTP has been resent."}, status=status.HTTP_200_OK)

    def _send_otp_email(self, is_temp, user):
        """Build and send OTP email. Returns True if sent successfully."""
        base = settings.FRONTEND_BASE_URL.rstrip("/")
        if is_temp:
            url = f"{base}/profile?is_email=true&email={user.email_temp}"
            html = render_to_string(
                "confirmation_mail.html",
                {"user": user, "otp": user.otp_secret, "domain": url},
            )
            return send_email(user.email_temp, "OTP Resend Confirmation", html)
        otp_link = f"{base}/account/{user.email}/otp"
        html = render_to_string(
            "confirmation_mail.html",
            {"user": user, "otp": user.otp_secret, "domain": otp_link},
        )
        return send_email(user.email, "OTP Resend Confirmation", html)

    def _issue_otp(self, is_temp, user: User) -> None:
        otp = generate_otp()
        user.otp_secret = otp
        user.otp_created_at = timezone.now()
        user.save(update_fields=["otp_secret", "otp_created_at"])

        Timer(60.0, clear_otp, [user]).start()
# class VerifyOtpView(APIView):
#     permission_classes = [AllowAny]

#     def post(self, request):
#         email= request.data.get('email')
#         entered_code = request.data.get('otp')
#         forget = self.request.query_params.get("forget", None)
#         is_email= self.request.query_params.get("change_email", None)
        
       


#         try:
#             user = User.objects.get(email=email)
#             print(user)
#         except User.DoesNotExist:
#             print("ll")
#             return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
#         if user.otp_secret =="" :
#             return Response({'error': 'expired verification code'}, status=status.HTTP_400_BAD_REQUEST)
#         if user.otp_secret == entered_code:
#             if forget:
#               user.is_forget_pass=True
#               user.save()
#             if is_email:
#               user.email=email
#               user.save()
#             user.is_verfied = True
#             user.save()
#             return Response({'message': 'Verification successful'}, status=status.HTTP_200_OK)
#         else:
#             return Response({'error': 'Invalid verification code'}, status=status.HTTP_400_BAD_REQUEST)



OTP_LIFETIME = timedelta(minutes=5)
class VerifyOtpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # ------------------------------------------------------------------
        # 1.  Basic validation
        # ------------------------------------------------------------------
        email = request.data.get("email")
        otp   = request.data.get("otp")

        if not email or not otp:
            return Response(
                {"detail": "Both 'email' and 'otp' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        forget       = request.query_params.get("forget") is not None
        change_email = request.query_params.get("change_email", "").lower() == "true"

        # ------------------------------------------------------------------
        # 2.  Fetch the user by the correct field
        # ------------------------------------------------------------------
        lookup_field = "email_temp" if change_email else "email"
        user = User.objects.filter(**{lookup_field: email}).first()

        if not user:
            return Response(
                {"detail": f"No user found with {lookup_field.replace('_', ' ')} = {email}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ------------------------------------------------------------------
        # 3.  OTP validity checks
        # ------------------------------------------------------------------
        if not user.otp_secret:
            return Response(
                {"detail": "Verification code has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.otp_secret != str(otp):
            return Response(
                {"detail": "Invalid verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional: check lifetime
        if user.otp_created_at and timezone.now() - user.otp_created_at > OTP_LIFETIME:
            return Response(
                {"detail": "Verification code has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ------------------------------------------------------------------
        # 4.  Apply side-effects for each flow
        # ------------------------------------------------------------------
        if forget:
            user.is_forget_pass = True

        if change_email:
            user.email = user.email_temp
            user.email_temp = None
            user.is_email_changed = False
            

        user.is_verfied = True
        user.otp_secret = ""           # consume the code
        user.otp_created_at = None
        user.save()

        return Response({"message": "Verification successful"}, status=status.HTTP_200_OK)

    
class ChangeForgotPassword(APIView):
    permission_classes = [AllowAny]

    def put(self, request, *args, **kwargs):
       
        new_password = request.data.get('new_password')
        confirm_new_password = request.data.get('confirm_password')
        email = request.data.get('email')

        if   not new_password or not email or not confirm_new_password:
            return Response({"error": "You must send  phone number, and the new password."},
                            status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_new_password:
            return Response({"error": "New password and confirm new password do not match."},
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if not  user.is_forget_pass:
          return Response({"error": "You are not permitted to change password. please go to verfiy your otp"},status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.change_password_at = timezone.now()
        user.is_forget_pass=False
        user.save()
        return Response({"success": "Password changed successfully"}, status=status.HTTP_200_OK)
        
        
        

   
# class UserUpdateView(generics.RetrieveUpdateAPIView):
#     serializer_class = UserSerializer
   
   

#     def get_object(self):
     
#         user = self.request.user
        
#         if isinstance(user, User):
#             return user
#         else:
         
#             return Response({'error': 'user not found'}, status=status.HTTP_404_NOT_FOUND)

#     def perform_update(self, serializer):
       
# #         user = serializer.save()
# from django.contrib.auth.password_validation import validate_password

# class UserUpdateView(generics.RetrieveUpdateAPIView):
#     serializer_class = UserSerializer
    

#     # -- the logged-in user *is* the target object ------------
#     def get_object(self):
#         return self.request.user
#     def update(self, request, *args, **kwargs):
        
#         kwargs['partial'] = True 
#         return super().update(request, *args, **kwargs)

#     # -- override save logic ---------------------------------
# class UserUpdateView(generics.RetrieveUpdateAPIView):
#     serializer_class = UserSerializer

#     def get_object(self):
#         return self.request.user

#     def update(self, request, *args, **kwargs):
#         kwargs['partial'] = True
#         return super().update(request, *args, **kwargs)

#     def perform_update(self, serializer):
#         new_email = self.request.data.get("email")
#         new_password = self.request.data.get("password")
#         print(new_password )
#         user = self.request.user

#         # 1. If no email in payload → do the normal save
#         if not new_email:
#             serializer.save()
#             return

#         # 2. Make sure the address is free
#         if User.objects.filter(email=new_email).exclude(pk=self.request.user.pk).exists():
#             raise ValidationError({"email": "This e-mail address is already in use."})

#         # 3. Validate password only if provided
#         # if new_password:
#         #     try:
#         #         validate_password(new_password, user=user)
#         #     except ValidationError as e:
#         #         # Catch the password validation errors and return them in the response
#         #         return Response(
#         #             {"password": e.messages}, status=status.HTTP_400_BAD_REQUEST
#         #         )

#         # 4. Strip the email field from validated_data so it won't overwrite the real email column
#         serializer.validated_data.pop("email", None)

#         # 5. Save all the other fields first
#         user = serializer.save()

#         # 6. Stash the new address in email_temp
#         user.email_temp = new_email
#         user.is_email_changed = True
#         user.save(update_fields=["email_temp", "is_email_changed"])

#         # 7. If a new password is provided, update the password
#         if new_password:
#             # user.set_password(new_password)
#             user.password = make_password(new_password)
#             user.change_password_at=timezone.now() 
            
            
#             user.save()
#             user.save(update_fields=[
            
#             "password",
#             "change_password_at",
#         ])
#             print(user.password)
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import ValidationError as DRFValidationError

class UserUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def perform_update(self, serializer):
        user         = self.request.user
        new_email    = self.request.data.get("email")
        new_password = self.request.data.get("password")

        # Strip these so DRF doesn’t write them raw
        serializer.validated_data.pop("email", None)
        serializer.validated_data.pop("password", None)

        serializer.save()   # save the other fields first

        # ----- e‑mail change ---------------------------------------------------
        if new_email and new_email != user.email:
            if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                raise DRFValidationError(
                    {"email": ["This e‑mail address is already in use."]})
            user.email_temp       = new_email
            user.is_email_changed = True

        # ----- password change -------------------------------------------------
        if new_password:
            try:
                validate_password(new_password, user=user)
            except DjangoValidationError as exc:
                raise DRFValidationError({"password": exc.messages})

            user.set_password(new_password)

            # ↙︎ here’s the “same time tomorrow” bit
            if new_email:  # changing both e‑mail and password
                user.change_password_at = timezone.now() + timedelta(days=1)
            else:          # only password is being changed
                user.change_password_at = timezone.now()

        # ----- persist tweaks --------------------------------------------------
        user.save(update_fields=[
            "email_temp",
            "is_email_changed",
            "password",
            "change_password_at",
        ])

class PartnerListCreateAPIView(generics.ListCreateAPIView):
    # Public read, admin-only write
    # (IsAdminForUnsafeMethods allows SAFE methods for all)
    permission_classes = [IsAdminForUnsafeMethods]
    queryset = Partners.objects.all()
    serializer_class = PartnerSerializer
    
    
    
class ContactUsListCreateView(generics.ListCreateAPIView):
    permission_classes = [AllowAny]
    queryset = ContactMessage.objects.all().order_by('-created_at')
    serializer_class = ContactMessageSerializer
    
    
from django.db.models import Q


class UserListAdminView(generics.ListAPIView):
    serializer_class = UserListAminSerializer
    permission_classes = [IsAdmin]
    pagination_class = TenPagePagination 
    # Add your custom permission if needed

    def get_queryset(self):
        queryset = User.objects.all()

        # Search by full name
        

        # Search by email
        search = self.request.query_params.get('search')
        if search:
              queryset = queryset.filter(
        Q(email__icontains=search) |
        Q(phone__icontains=search) |
        Q(full_name__icontains=search)
    )

        # Filter by role
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)

        return queryset
    
class AddAdminView(generics.CreateAPIView):
    permission_classes = [IsAdmin]
    queryset = User.objects.all()
    serializer_class = UserAddInAdminSerializer

    def create(self, request, *args, **kwargs):
        required_fields = ['email', 'password']

        # Ensure required fields exist
        for field in required_fields:
            if field not in request.data:
                raise ValidationError({field: ["This field is required."]})

        password = request.data.get("password")

        # Inject 'admin' role before validation
        data = request.data.copy()
        data['role'] = 'admin'  # or use User.Role.ADMIN if it's an enum or class constant

        # Create the user with role
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate token after user creation
        token = generate_jwt_token(user)

        # Prepare and send email (use full login URL from settings so link is always correct)
        login_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/account/login"
        html_content = render_to_string('add_user.html', {
            "token": token,
            "password": password,
            "user": user,
            "domain": urlparse(settings.FRONTEND_BASE_URL).netloc or "ken.mernantech.com",
            "login_url": login_url,
        })

        send_email(user.email, "KEN - New Account Created", html_content)

        return Response({
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)






class AddUpplierView(generics.CreateAPIView):
    # permission_classes = [] 
    queryset = User.objects.all()

    serializer_class = SupplierAddSerializer

    def create(self, request, *args, **kwargs):
        required_fields = ['email', 'password']

        # Ensure required fields exist
        for field in required_fields:
            if field not in request.data:
                raise ValidationError({field: ["This field is required."]})

        password = request.data.get("password")

        # Create the user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate token after user creation
        token = generate_jwt_token(user)

        # Prepare and send email (use full login URL from settings so link is always correct)
        login_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/account/login"
        html_content = render_to_string('add_user.html', {
            "token": token,
            "password": password,
            "user": user,
            "domain": urlparse(settings.FRONTEND_BASE_URL).netloc or "ken.mernantech.com",
            "login_url": login_url,
        })

        send_email(user.email, "KEN - New Account Created", html_content)

        return Response({
           
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)




class AddGuestView(generics.CreateAPIView):
    permission_classes = [IsAdmin]
    queryset = User.objects.all()
    serializer_class = UserAddInAdminSerializer

    def create(self, request, *args, **kwargs):
        required_fields = ['email', 'password']

        # Ensure required fields exist
        for field in required_fields:
            if field not in request.data:
                raise ValidationError({field: ["This field is required."]})

        password = request.data.get("password")

        # Copy data and inject 'role': 'GUEST'
        data = request.data.copy()
        data['role'] = 'guest'

        # Validate and create user
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate token
        token = generate_jwt_token(user)

        # Prepare and send email (use full login URL from settings so link is always correct)
        login_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/account/login"
        html_content = render_to_string('add_user.html', {
            "token": token,
            "password": password,
            "user": user,
            "domain": urlparse(settings.FRONTEND_BASE_URL).netloc or "ken.mernantech.com",
            "login_url": login_url,
        })

        send_email(user.email, "KEN - New Account Created", html_content)

        return Response({
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)


class UserDetailInAdminView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = SupplierAddSerializer
    permission_classes = [IsAdmin]
    lookup_field = 'pk'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.pk == request.user.pk:
            return Response(
                {"error": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ProtectedError:
            return Response(
                {"error": "Cannot delete user: this user has related data that must be removed or reassigned first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RestrictedError:
            return Response(
                {"error": "Cannot delete user: related records prevent this deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                {"error": "Cannot delete user due to database constraints."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            import logging
            logging.getLogger(__name__).exception("User delete failed for pk=%s", instance.pk)
            message = "Failed to delete user. Please try again or contact support."
            if getattr(settings, "DEBUG", False):
                message = f"{message} ({type(e).__name__}: {e})"
            return Response(
                {"error": message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def update(self, request, *args, **kwargs):
        partial = True
        instance = self.get_object()
        data = request.data.copy()

        password = data.pop('password', None)

        # If password is a list, get the first item
        if isinstance(password, list):
            password = password[0]

        # Convert password to string if it's a number (int/float)
        if password is not None and not isinstance(password, str):
            password = str(password)

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])

        return Response(serializer.data)




class SupportCreateView(generics.CreateAPIView):
    queryset = Support.objects.all()
    serializer_class = SupportSerializer
    permission_classes = []

    def perform_create(self, serializer):
     
     serializer.save()
     
     
     
class SupportListView(generics.ListAPIView):
    serializer_class = SupportSerializer
    permission_classes = [IsAdminOrSupplier]
    pagination_class = TenPagePagination
    filter_backends = [SearchFilter]
    search_fields = ['full_name', 'email', 'content']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'supplier':
            qs = Support.objects.filter(operation=user, is_admin=False).order_by('-created_at')
        else:
            qs = Support.objects.filter(operation__isnull=True).order_by('-created_at')
        return qs
    
    
class SupportReplyView(APIView):
    permission_classes = [IsAdminOrSupplier]

    def post(self, request):
        support_id = request.data.get("support_id")
        reply_text = request.data.get("email")

        if not support_id or not reply_text:
            return Response({"error": "support_id and text are required."}, status=400)

        try:
            support = Support.objects.get(id=support_id)
        except Support.DoesNotExist:
            return Response({"error": "Support not found."}, status=404)

        # Prepare and send email
        html_content = render_to_string('support.html', {
            'user_name': support.full_name ,
            'reply_text': reply_text,
        })
        
        send_email(
            recipient_email=support.email,
            subject="Reply to your support request",
            html_content=html_content
        )

        # Mark as replied
        support.is_replied = True
        support.save()

        return Response({"message": "Reply sent and support marked as replied."}, status=200)
    
    


class SupplierListView(generics.ListAPIView):
    serializer_class = MiniUserSerializer
    permission_classes = []
    
  

    def get_queryset(self):
        queryset = User.objects.filter(role='supplier')
        return queryset

class SupportDetailView(generics.RetrieveAPIView):
    queryset = Support.objects.all()
    serializer_class = SupportSerializer
    permission_classes = [IsAdminOrSupplier]
    
    
    
    
    
    
    
    
    


class NotificationListView(generics.ListAPIView):
   
    serializer_class = NotificationSerializer
    pagination_class=TenPagePagination
    

    def get_queryset(self):
        user = self.request.user
        notif_type = self.request.query_params.get('type')  # e.g., ?type=review
        
        queryset = Notification.objects.filter(user=user)
        if notif_type:
            queryset = queryset.filter(type=notif_type)
        return queryset.order_by('-datetime')
    
    
    
    

class MarkNotificationAsRead(generics.UpdateAPIView):
    
    

    def put(self, request, *args, **kwargs):
        user = self.request.user
        pk = kwargs['pk']
        notification = get_object_or_404(Notification, pk=pk)
        notification.mark_as_read = True
        notification.save()
        return Response(status=status.HTTP_200_OK)
    



class GetNotificationCountView(generics.RetrieveAPIView):
    
    

    def get(self, request, *args, **kwargs):
        user = self.request.user
        
        queryset = Notification.objects.filter(user=user, mark_as_read=False).count()
       
            
       
       
        return Response({'notification_count': queryset})






class MarkAllNotificationsAsRead(APIView):
    def put(self, request, *args, **kwargs):
        user = request.user
        Notification.objects.filter(user=user, mark_as_read=False).update(mark_as_read=True)
        return Response({"detail": "All notifications marked as read."}, status=status.HTTP_200_OK)