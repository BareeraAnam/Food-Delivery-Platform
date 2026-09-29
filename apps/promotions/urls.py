from django.urls import path
from .views import PromoCodeListCreateView, PromoCodeValidateView, MyReferralRewardsView

urlpatterns = [
    path('', PromoCodeListCreateView.as_view(), name='promo-list-create'),
    path('validate/', PromoCodeValidateView.as_view(), name='promo-validate'),
    path('referrals/', MyReferralRewardsView.as_view(), name='my-referral-rewards'),
]
