import os
import shutil
import sqlite3
from django.core.management.base import BaseCommand
from django.conf import settings
from products.models import (
    Hut, Location, AvailableDateRanges, HutImages, PromoCode,
    HutMainService, HutActivity, Icon, Event, Services, EventInclude, EventNote, HutRating
)

class Command(BaseCommand):
    help = "Import data from ken_data/db.sqlite3 into current database and replace existing huts data"

    def handle(self, *args, **options):
        # 1. Locate ken_data directory
        possible_paths = [
            os.path.join(settings.BASE_DIR, "..", "ken_data"),
            os.path.join(settings.BASE_DIR, "ken_data"),
            r"c:\Users\hisha\OneDrive\Desktop\Ken\ken_data",
            "/var/task/ken_data"
        ]

        ken_data_dir = None
        for p in possible_paths:
            abs_p = os.path.abspath(p)
            if os.path.exists(os.path.join(abs_p, "db.sqlite3")):
                ken_data_dir = abs_p
                break

        if not ken_data_dir:
            self.stdout.write(self.style.ERROR("Could not find ken_data/db.sqlite3"))
            return

        db_path = os.path.join(ken_data_dir, "db.sqlite3")
        uploads_dir = os.path.join(ken_data_dir, "uploads")
        self.stdout.write(self.style.SUCCESS(f"Found ken_data at: {ken_data_dir}"))

        # 2. Copy uploads folder to MEDIA_ROOT
        if os.path.exists(uploads_dir):
            try:
                target_media = getattr(settings, 'MEDIA_ROOT', '/tmp/media')
                os.makedirs(target_media, exist_ok=True)
                for root, dirs, files in os.walk(uploads_dir):
                    rel_path = os.path.relpath(root, uploads_dir)
                    dest_dir = os.path.join(target_media, rel_path) if rel_path != '.' else target_media
                    os.makedirs(dest_dir, exist_ok=True)
                    for f in files:
                        src_file = os.path.join(root, f)
                        dst_file = os.path.join(dest_dir, f)
                        shutil.copy2(src_file, dst_file)
                self.stdout.write(self.style.SUCCESS(f"Copied uploaded files to {target_media}"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Uploads copy warning: {e}"))

        # 3. Connect to SQLite source database
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 4. Clear current huts and related data from current database
        self.stdout.write("Deleting existing huts data...")
        HutRating.objects.all().delete()
        HutActivity.objects.all().delete()
        HutMainService.objects.all().delete()
        AvailableDateRanges.objects.all().delete()
        Hut.objects.all().delete()
        HutImages.objects.all().delete()
        PromoCode.objects.all().delete()
        Location.objects.all().delete()
        Icon.objects.all().delete()
        EventInclude.objects.all().delete()
        EventNote.objects.all().delete()
        Event.objects.all().delete()
        Services.objects.all().delete()

        def make_cdn_url(img_path):
            if not img_path:
                return img_path
            if str(img_path).startswith("http"):
                return img_path
            clean_path = str(img_path).lstrip("/")
            return f"https://didujlgaqnfziazqooxo.supabase.co/storage/v1/object/public/media/{clean_path}"

        # 5. Import Icons
        cur.execute("SELECT id, image FROM products_icon")
        for row in cur.fetchall():
            Icon.objects.create(id=row[0], image=make_cdn_url(row[1]))
        self.stdout.write("Imported Icons")

        # 6. Import Locations
        cur.execute("SELECT id, latitude, longitude, address, address_ar FROM products_location")
        for row in cur.fetchall():
            Location.objects.create(
                id=row[0],
                latitude=row[1],
                longitude=row[2],
                address=row[3],
                address_ar=row[4]
            )
        self.stdout.write("Imported Locations")

        # 7. Import PromoCodes
        cur.execute("SELECT id, code, is_active, created_at, percentage FROM products_promocode")
        for row in cur.fetchall():
            PromoCode.objects.create(
                id=row[0],
                code=row[1],
                is_active=bool(row[2]),
                percentage=row[4] or 0
            )
        self.stdout.write("Imported PromoCodes")

        # 8. Import HutImages
        cur.execute("SELECT id, image FROM products_hutimages")
        for row in cur.fetchall():
            HutImages.objects.create(id=row[0], image=make_cdn_url(row[1]))
        self.stdout.write("Imported HutImages")

        # 9. Import Huts
        cur.execute("""
            SELECT id, title, title_ar, description, description_ar, size, rate, created_at, 
                   main_image, max_kids_num, bedrooms_num, bathrooms_num, max_persons_num, 
                   is_active, check_in, check_out, macc_address, location_id 
            FROM products_hut
        """)
        for row in cur.fetchall():
            loc = Location.objects.filter(id=row[17]).first() if row[17] else None
            hut = Hut.objects.create(
                id=row[0],
                title=row[1],
                title_ar=row[2],
                description=row[3],
                description_ar=row[4],
                size=row[5],
                rate=row[6] or 0.00,
                main_image=make_cdn_url(row[8]),
                max_kids_num=row[9],
                bedrooms_num=row[10],
                bathrooms_num=row[11],
                max_persons_num=row[12],
                is_active=bool(row[13]),
                check_in=row[14],
                check_out=row[15],
                macc_address=row[16],
                location=loc
            )

        # 10. Link HutImages M2M
        cur.execute("SELECT hut_id, hutimages_id FROM products_hut_images")
        for hut_id, img_id in cur.fetchall():
            hut = Hut.objects.filter(id=hut_id).first()
            img = HutImages.objects.filter(id=img_id).first()
            if hut and img:
                hut.images.add(img)

        # 11. Link Hut PromoCode M2M
        cur.execute("SELECT hut_id, promocode_id FROM products_hut_promocode")
        for hut_id, promo_id in cur.fetchall():
            hut = Hut.objects.filter(id=hut_id).first()
            promo = PromoCode.objects.filter(id=promo_id).first()
            if hut and promo:
                hut.promocode.add(promo)

        self.stdout.write("Imported Huts and relationships")

        # 12. Import AvailableDateRanges
        cur.execute("SELECT id, date_from, date_to, price, promo_code, precentage, huts_id FROM products_availabledateranges")
        for row in cur.fetchall():
            hut = Hut.objects.filter(id=row[6]).first()
            if hut:
                AvailableDateRanges.objects.create(
                    id=row[0],
                    date_from=row[1],
                    date_to=row[2],
                    price=row[3],
                    promo_code=row[4],
                    precentage=row[5],
                    huts=hut
                )
        self.stdout.write("Imported AvailableDateRanges")

        # 13. Import HutMainService
        cur.execute("SELECT id, description, description_ar, is_extra, hut_id, icon_id FROM products_hutmainservice")
        for row in cur.fetchall():
            hut = Hut.objects.filter(id=row[4]).first()
            icon = Icon.objects.filter(id=row[5]).first() if row[5] else None
            if hut:
                HutMainService.objects.create(
                    id=row[0],
                    description=row[1],
                    description_ar=row[2],
                    is_extra=bool(row[3]),
                    hut=hut,
                    icon=icon
                )
        self.stdout.write("Imported HutMainServices")

        # 14. Import HutActivity
        cur.execute("SELECT id, description, description_ar, hut_id FROM products_hutactivity")
        for row in cur.fetchall():
            hut = Hut.objects.filter(id=row[3]).first()
            if hut:
                HutActivity.objects.create(
                    id=row[0],
                    description=row[1],
                    description_ar=row[2],
                    hut=hut
                )
        self.stdout.write("Imported HutActivities")

        # 15. Import Services
        cur.execute("""
            SELECT id, image, title, title_ar, description, description_ar, price, capacity,
                   min_purchasable_quantity, max_purchasable_quantity, is_active, is_delete, hut_id, supplier_id
            FROM products_services
        """)
        for row in cur.fetchall():
            hut = Hut.objects.filter(id=row[12]).first() if row[12] else None
            Services.objects.create(
                id=row[0],
                image=make_cdn_url(row[1]),
                title=row[2],
                title_ar=row[3],
                description=row[4],
                description_ar=row[5],
                price=row[6],
                capacity=row[7],
                min_purchasable_quantity=row[8],
                max_purchasable_quantity=row[9],
                is_active=bool(row[10]),
                is_delete=bool(row[11]),
                hut=hut,
                supplier_id=row[13]
            )
        self.stdout.write("Imported Services")

        # 16. Import Events
        cur.execute("""
            SELECT id, title, title_ar, description, description_ar, rate, capacity, created_at,
                   image, min_purchasable_quantity, max_purchasable_quantity, is_active, is_delete, hut_id, location_id, supplier_id
            FROM products_event
        """)
        for row in cur.fetchall():
            hut = Hut.objects.filter(id=row[13]).first() if row[13] else None
            loc = Location.objects.filter(id=row[14]).first() if row[14] else None
            Event.objects.create(
                id=row[0],
                title=row[1],
                title_ar=row[2],
                description=row[3],
                description_ar=row[4],
                rate=row[5] or 0.00,
                capacity=row[6],
                image=make_cdn_url(row[8]),
                min_purchasable_quantity=row[9],
                max_purchasable_quantity=row[10],
                is_active=bool(row[11]),
                is_delete=bool(row[12]),
                hut=hut,
                location=loc,
                supplier_id=row[15]
            )
        self.stdout.write("Imported Events")

        conn.close()

        # Ensure Admin User exists
        try:
            from accounts.models import User
            admin_user, created = User.objects.get_or_create(
                email='admin@kenluxuryreef.com',
                defaults={
                    'first_name': 'Admin',
                    'last_name': 'Ken',
                    'role': 'admin',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True
                }
            )
            admin_user.set_password('admin123')
            admin_user.role = 'admin'
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.save()
            self.stdout.write("Ensured admin user admin@kenluxuryreef.com")
        except Exception as e:
            self.stdout.write(f"Admin user creation warning: {e}")

        self.stdout.write(self.style.SUCCESS("All ken_data imported successfully!"))
