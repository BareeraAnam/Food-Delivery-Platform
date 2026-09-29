import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.restaurants.models import Restaurant, MenuCategory, MenuItem

for r in Restaurant.objects.all():
    cat, _ = MenuCategory.objects.get_or_create(
        restaurant=r, name='Main Menu', defaults={'display_order': 1}
    )
    base = int(r.minimum_order_amount)
    items = [
        (f'{r.name} Special', base + 100),
        (f'{r.name} Family Deal', base + 300),
        (f'{r.name} Combo', base + 200),
    ]
    print(f'\n{r.name} | slug: {r.slug} | restaurant_id: {r.id}')
    for name, price in items:
        item, _ = MenuItem.objects.get_or_create(
            restaurant=r, category=cat, name=name,
            defaults={'price': price, 'is_available': True},
        )
        print(f'   - {item.name} | Rs {item.price} | menu_item_id: {item.id}')
