from rest_framework import serializers
from .models import *
from django.contrib.auth.hashers import check_password
from rest_framework.response import Response
from rest_framework  import status


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ['email', 'password', 'role', 'full_name', 'gender', 'avatar', 'address', 'birth_date', 'phone', 'id_num', 'is_active']

    def validate_email(self, value):
        email = value.lower()
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise serializers.ValidationError("Email is already in use.")
        return email

    def validate_phone(self, value):
        if not value.startswith('+966') and not value.startswith('+02'):
          raise serializers.ValidationError("Phone number must start with +966 or +02.")
        user_id = self.instance.id if self.instance else None
        
        if User.objects.filter(phone=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("Phone number is already in use.")
        return value
    def validate_id_num(self, value):
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(id_num=value).exclude(id=user_id).exists():
            raise serializers.ValidationError(" id_num  is already  exsit")
        return value


    def create(self, validated_data):
        validated_data['role'] = 'guest'
        validated_data['is_active'] = True
        if User.objects.filter(email=validated_data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})
        
        user = User.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

        return user
   
# class LoginSerializer(serializers.ModelSerializer):
#     email=serializers.EmailField()
#     password=serializers.CharField(write_only=True)
    
#     class Meta:
#         model = User
#         fields = ['email', 'password']
#     def validate(self,data):
#         email=data.get('email')
#         password=data.get('password')
#         user=None
#         try:
#             user = User.objects.get(email=email)
#         except User.DoesNotExist: 
#             raise serializers.ValidationError("User not found")

        
#         if user and not check_password(password, user.password):

#             raise serializers.validationError("passowrd not correct")
#         if not user.is_verfied:
#             raise serializers.ValidationError("This user is not verfied")
#         return {'user': user}
    
    

class LoginSerializer(serializers.Serializer):          # Plain Serializer is fine here
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        # 1. Does the user exist?
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        # 2. Is the password correct?
        if not check_password(password, user.password):
            raise serializers.ValidationError({"password": "Password is not correct."})

        # 3. Is the account verified? (Superusers, staff, and admin role can bypass verification)
        if not user.is_superuser and not user.is_staff and user.role != "admin" and not getattr(user, "is_verfied", False):
            raise serializers.ValidationError("This user is not verified.")

        # 4. Stick the user on the validated data and return it
        attrs["user"] = user
        return attrs


class MiniUserSerializer(serializers.ModelSerializer):
  

    class Meta:
        model = User
        fields = [ 'id','role', 'full_name', 'avatar','email','phone']
        

class UserListAminSerializer(serializers.ModelSerializer):
  

    class Meta:
        model = User
        fields = [ 'id','role', 'full_name', 'avatar','email','phone']
        
        
        
        
        
        

class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partners
        fields = ['id', 'image']
        
        
        
        
        
        
        
class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']
        
        



class UserAddInAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = User
        fields = ['email', 'password', 'role', 'full_name', 'gender', 'avatar', 'address', 'birth_date', 'phone', 'id_num', 'is_active']

    def validate_email(self, value):
        email = value.lower()
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise serializers.ValidationError("Email is already in use.")
        return email

    def validate_phone(self, value):
        if not value.startswith('+966') :
          raise serializers.ValidationError("Phone number must start with +966 or +02.")
        user_id = self.instance.id if self.instance else None
        
        if User.objects.filter(phone=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("Phone number is already in use.")
        return value
    def validate_id_num(self, value):
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(id_num=value).exclude(id=user_id).exists():
            raise serializers.ValidationError(" id_num  is already  exsit")
        return value


    def create(self, validated_data):
        # validated_data['role'] = 'guest'
        validated_data['is_active'] = True
        # validated_data['role'] = 'admin'
        validated_data['is_verfied'] = True
        if User.objects.filter(email=validated_data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})
        
        user = User.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

        return user
    
    


class SupplierAddSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    phone=serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ['id','email', 'password', 'role', 'full_name', 'gender', 'avatar', 'address', 'birth_date', 'phone', 'id_num', 'is_active','breif']

    def validate_email(self, value):
        email = value.lower()
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(email=email).exclude(id=user_id).exists():
            raise serializers.ValidationError("Email is already in use.")
        return email

    def validate_phone(self, value):
        if not value.startswith('+966') :
          raise serializers.ValidationError("Phone number must start with +966 or +02.")
        user_id = self.instance.id if self.instance else None
        
        if User.objects.filter(phone=value).exclude(id=user_id).exists():
            raise serializers.ValidationError("Phone number is already in use.")
        return value
    def validate_id_num(self, value):
        user_id = self.instance.id if self.instance else None
        if User.objects.filter(id_num=value).exclude(id=user_id).exists():
            raise serializers.ValidationError(" id_num  is already  exsit")
        return value


    def create(self, validated_data):
        # validated_data['role'] = 'guest'
        validated_data['is_active'] = True
        validated_data['role'] = 'supplier'
        validated_data['is_verfied'] = True
        if User.objects.filter(email=validated_data['email']).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})
        
        user = User.objects.create(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

        return user
   
   



class SupportSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = Support
        fields = ['id', 'full_name', 'email', 'content', 'attachment', 'is_replied', 'created_at','operation','is_admin']
        read_only_fields = ['id', 'user', 'is_replied', 'created_at']
        
        
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'