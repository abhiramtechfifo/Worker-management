from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response


def _user_payload(user, token_key=None):
    data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    }
    if token_key is not None:
        data['token'] = token_key
    return data


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def login_view(request):
    """Authenticate with username + password and return a token."""
    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''
    if not username or not password:
        return Response(
            {'detail': 'Username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return Response(
            {'detail': 'Invalid username or password.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )
    if not user.is_active:
        return Response(
            {'detail': 'This account is disabled.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response(_user_payload(user, token.key))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Invalidate the caller's token."""
    Token.objects.filter(user=request.user).delete()
    return Response({'detail': 'Logged out.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """Return information about the current user."""
    return Response(_user_payload(request.user))


@api_view(['POST'])
@permission_classes([AllowAny])
@authentication_classes([])
def register_view(request):
    """
    Create an admin user. Protected by the X-Admin-Secret header which must
    match the ADMIN_REGISTER_SECRET setting. Intended for Postman use only.
    """
    provided_secret = request.headers.get('X-Admin-Secret', '')
    expected_secret = getattr(settings, 'ADMIN_REGISTER_SECRET', None)
    if not expected_secret or provided_secret != expected_secret:
        return Response(
            {'detail': 'Forbidden.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    username = (request.data.get('username') or '').strip()
    password = request.data.get('password') or ''
    email = (request.data.get('email') or '').strip()
    if not username or not password:
        return Response(
            {'detail': 'Username and password are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if User.objects.filter(username=username).exists():
        return Response(
            {'detail': 'A user with that username already exists.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        is_staff=True,
        is_superuser=True,
    )
    token, _ = Token.objects.get_or_create(user=user)
    return Response(_user_payload(user, token.key), status=status.HTTP_201_CREATED)
