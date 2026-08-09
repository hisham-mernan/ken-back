import os
from datetime import date, timedelta, time
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import Partners, Support, WebRating, WebsiteRate, Notification
from content.models import (
    AboutUs, FAQ, Story, OurService, SpecailAboutUs,
    TermsAndCindations, TermsAndCindationsTitle, WebStoreRating, WebStore
)
from products.models import (
    Hut, Location, AvailableDateRanges, HutImages, PromoCode,
    HutMainService, HutActivity, Icon, Event, Services, EventInclude,
    EventNote, HutRating, AvailableDateEvent, AvailableDateService, KenSpecialItems,
    Booking, BookingDate, EventTicket, ServiceTicket
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seed database with reverted hut titles, 8+ bilingual events, 8+ services, and complete dashboard metrics through 2026/12/31."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding database with expanded bilingual data & dashboard metrics..."))

        # 1. Clear existing data
        BookingDate.objects.all().delete()
        EventTicket.objects.all().delete()
        ServiceTicket.objects.all().delete()
        Booking.objects.all().delete()
        HutRating.objects.all().delete()
        HutActivity.objects.all().delete()
        HutMainService.objects.all().delete()
        AvailableDateRanges.objects.all().delete()
        AvailableDateEvent.objects.all().delete()
        AvailableDateService.objects.all().delete()
        Hut.objects.all().delete()
        HutImages.objects.all().delete()
        PromoCode.objects.all().delete()
        Location.objects.all().delete()
        Icon.objects.all().delete()
        EventInclude.objects.all().delete()
        EventNote.objects.all().delete()
        Event.objects.all().delete()
        Services.objects.all().delete()
        KenSpecialItems.objects.all().delete()
        AboutUs.objects.all().delete()
        FAQ.objects.all().delete()
        Story.objects.all().delete()
        OurService.objects.all().delete()
        SpecailAboutUs.objects.all().delete()
        TermsAndCindations.objects.all().delete()
        TermsAndCindationsTitle.objects.all().delete()
        Support.objects.all().delete()
        Notification.objects.all().delete()
        Partners.objects.all().delete()

        # 2. Seed Users & Suppliers
        self.stdout.write("Seeding Admin & Supplier accounts...")
        admin_user, _ = User.objects.get_or_create(
            email='admin@kenluxuryreef.com',
            defaults={
                'first_name': 'Admin',
                'last_name': 'Ken',
                'full_name': 'Ken Admin / إدارة كِن',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
                'phone': '+966500000000',
            }
        )
        admin_user.set_password('admin123')
        admin_user.save()

        supplier1, _ = User.objects.get_or_create(
            email='supplier1@kenluxuryreef.com',
            defaults={
                'first_name': 'Red Sea',
                'last_name': 'Adventures',
                'full_name': 'Red Sea Adventures / مغامرات البحر الأحمر',
                'role': 'supplier',
                'is_active': True,
                'phone': '+966500000001',
                'breif': 'Premier Red Sea marine experiences provider.'
            }
        )
        supplier1.set_password('supplier123')
        supplier1.save()

        supplier2, _ = User.objects.get_or_create(
            email='supplier2@kenluxuryreef.com',
            defaults={
                'first_name': 'Desert Reef',
                'last_name': 'Hospitality',
                'full_name': 'Desert Reef Hospitality / ضيافة شعب الصحراء',
                'role': 'supplier',
                'is_active': True,
                'phone': '+966500000002',
                'breif': 'Authentic Saudi coastal culinary & desert shore events.'
            }
        )
        supplier2.set_password('supplier123')
        supplier2.save()

        guest1, _ = User.objects.get_or_create(
            email='guest1@kenluxuryreef.com',
            defaults={
                'first_name': 'Ahmed',
                'last_name': 'Al-Otaibi',
                'full_name': 'Ahmed Al-Otaibi / أحمد العتيبي',
                'role': 'guest',
                'is_active': True,
                'phone': '+966500000003',
            }
        )
        guest1.set_password('guest123')
        guest1.save()

        # 3. Seed Locations
        self.stdout.write("Seeding Locations...")
        loc1 = Location.objects.create(
            latitude=21.5433,
            longitude=39.1728,
            address="Coral Bay Beachfront, North Corniche, Jeddah",
            address_ar="شاطئ خليج المرجان، الكورنيش الشمالي، جدة"
        )
        loc2 = Location.objects.create(
            latitude=24.0891,
            longitude=38.0618,
            address="Royal Reef Sanctuary, Yanbu Al Bahr",
            address_ar="محمية المرجان الملكية، ينبع البحر"
        )
        loc3 = Location.objects.create(
            latitude=26.2172,
            longitude=50.1971,
            address="Palm Oasis Shore, Al Khobar",
            address_ar="شاطئ واحة النخيل، الخبر"
        )

        # 4. Seed Icons
        self.stdout.write("Seeding Icons...")
        icon_wifi = Icon.objects.create(image="uploads/services/icons/wifi.png")
        icon_pool = Icon.objects.create(image="uploads/services/icons/pool.png")
        icon_ocean = Icon.objects.create(image="uploads/services/icons/ocean.png")
        icon_bbq = Icon.objects.create(image="uploads/services/icons/bbq.png")
        icon_ac = Icon.objects.create(image="uploads/services/icons/ac.png")

        # 5. Seed PromoCodes
        self.stdout.write("Seeding PromoCodes...")
        promo1 = PromoCode.objects.create(code="SUMMER2026", percentage=20, is_active=True)
        promo2 = PromoCode.objects.create(code="KENLUXURY", percentage=15, is_active=True)
        promo3 = PromoCode.objects.create(code="WELCOME10", percentage=10, is_active=True)

        # 6. Seed Huts (REVERTED TITLES: Wahad Hut, Malath Hut, Qimma Hut)
        self.stdout.write("Seeding Luxury Huts (Reverted Titles)...")
        hut1 = Hut.objects.create(
            id=2,
            title="Wahad Hut",
            title_ar="كوخ واحة",
            description="Experience ultimate serene coastal luxury over crystal-clear Red Sea waters with private infinity deck and personal butler service.",
            description_ar="استمتع بأقصى درجات الرفاهية والهدوء الساحلي فوق مياه البحر الأحمر الكريستالية مع سطح خاص وإطلالة بانورامية ساحرة.",
            size="large",
            rate=4.90,
            main_image="uploads/services/hut_image/hut1.jpg",
            max_kids_num=4,
            bedrooms_num=3,
            bathrooms_num=2,
            max_persons_num=6,
            is_active=True,
            check_in=time(14, 0),
            check_out=time(12, 0),
            macc_address="KEN-REEF-01",
            location=loc1
        )
        hut1.promocode.add(promo1, promo2)

        hut2 = Hut.objects.create(
            id=3,
            title="Malath Hut",
            title_ar="كوخ ملاذ",
            description="An intimate beachfront sanctuary featuring panoramic ocean sunsets, private heated jacuzzi, and direct reef snorkeling access.",
            description_ar="ملاذ شاطئي خاص وساحر يتميز بملحق جاكوزي دافئ وإطلالة بانورامية كاملة على غروب البحر ودخول مباشر لغوص المرجان.",
            size="meduim",
            rate=4.85,
            main_image="uploads/services/hut_image/hut2.jpg",
            max_kids_num=2,
            bedrooms_num=2,
            bathrooms_num=2,
            max_persons_num=4,
            is_active=True,
            check_in=time(15, 0),
            check_out=time(12, 0),
            macc_address="KEN-REEF-02",
            location=loc2
        )
        hut2.promocode.add(promo2, promo3)

        hut3 = Hut.objects.create(
            id=4,
            title="Qimma Hut",
            title_ar="كوخ قمة",
            description="Our flagship 4-bedroom overwater masterpiece with transparent glass floor viewing gallery, private plunge pool, and gourmet dining space.",
            description_ar="تحفتنا المعمارية الملكية فوق الماء بـ 4 غرف نوم وأرضية زجاجية شفافة لمشاهدة المرجان ومسبح خاص وتراس لتناول الطعام المتميز.",
            size="large",
            rate=5.00,
            main_image="uploads/services/hut_image/hut3.jpg",
            max_kids_num=4,
            bedrooms_num=4,
            bathrooms_num=3,
            max_persons_num=8,
            is_active=True,
            check_in=time(14, 0),
            check_out=time(11, 0),
            macc_address="KEN-REEF-03",
            location=loc3
        )
        hut3.promocode.add(promo1, promo3)

        # Available Date Ranges for Huts (until 2026-12-31)
        AvailableDateRanges.objects.create(huts=hut1, date_from="2026-01-01", date_to="2026-12-31", price=700.00)
        AvailableDateRanges.objects.create(huts=hut2, date_from="2026-01-01", date_to="2026-12-31", price=1000.00)
        AvailableDateRanges.objects.create(huts=hut3, date_from="2026-01-01", date_to="2026-12-31", price=1500.00)

        # Hut Services & Activities
        HutMainService.objects.create(hut=hut1, icon=icon_wifi, description="High-Speed Satellite Wi-Fi", description_ar="إنترنت فضائي سريع جداً", is_extra=False)
        HutMainService.objects.create(hut=hut1, icon=icon_ocean, description="Private Sea View Deck", description_ar="سطح خاص بجلوس على البحر", is_extra=False)
        HutMainService.objects.create(hut=hut1, icon=icon_bbq, description="Private BBQ Set & Chef", description_ar="طقم شواء خاص وشيف عند الطلب", is_extra=True)
        HutActivity.objects.create(hut=hut1, description="Coral Reef Snorkeling & Kayaking", description_ar="غوص الشعب المرجانية وقوارب الكاياك")

        HutMainService.objects.create(hut=hut2, icon=icon_pool, description="Private Heated Jacuzzi", description_ar="جاكوزي خاص مجهز بنظام التدفئة", is_extra=False)
        HutMainService.objects.create(hut=hut2, icon=icon_ac, description="Smart Climate Control", description_ar="تكييف ذكي متكامل", is_extra=False)
        HutActivity.objects.create(hut=hut2, description="Sunset Yacht Tours & Paddleboarding", description_ar="جولات اليخت وقت الغروب والتجديف")

        HutMainService.objects.create(hut=hut3, icon=icon_ocean, description="Glass Floor Glass Reef Window", description_ar="نافذة أرضية زجاجية لمشاهدة الشعب المرجانية", is_extra=False)
        HutMainService.objects.create(hut=hut3, icon=icon_pool, description="Overwater Infinity Pool", description_ar="مسبح انفينيتي ملكي فوق الماء", is_extra=False)
        HutActivity.objects.create(hut=hut3, description="Deep Sea Fishing & Scuba Expeditions", description_ar="رحلات الصيد البحري والغوص الحر")

        # 7. Seed Expanded Events (8 Events)
        self.stdout.write("Seeding 8+ Expanded Events...")
        events_data = [
            ("Red Sea Sunset BBQ & Marine Gala", "حفل عشاء وشواء غروب البحر الأحمر", "An unforgettable evening featuring freshly grilled seafood, live acoustic melodies, and guided night ocean observation.", "أمسية ساحرة لا تُنسى تتضمن مأكولات بحرية طازجة ومشوية، وعزف موسيقي حاد، ومراقبة الكائنات البحرية ليلاً.", 1200.00, 15, supplier1, loc1, hut1),
            ("Reef Diving & Coral Conservation Tour", "جولة الغوص واستكشاف شعب المرجان", "Guided scuba diving trip led by marine biologists exploring untouched coral reefs and rare sea turtles.", "رحلة غوص استكشافية برفقة خبراء أحياء بحرية لاستكشاف الشعب المرجانية العذراء والسلاحف البحرية النادرة.", 850.00, 12, supplier1, loc2, hut2),
            ("Stargazing Desert Shore Night", "ليلة التخييم ومراقبة النجوم على الشاطئ", "A magical night of telescope astronomy, traditional campfire tales, and traditional Saudi hospitality under the stars.", "ليلة ساحرة لرصد النجوم بالتلسكوبات، وحكايات السمر حول شبة النار والضيافة السعودية الأصيلة تحت النجوم.", 650.00, 20, supplier2, loc3, hut3),
            ("Luxury Private Yacht Party & Live DJ", "حفل يخت خاص فاخر مع دي جي", "Exclusive sunset cruise on a 75ft motor yacht with live DJ performance and gourmet catering.", "رحلة يخت فاخر عند الغروب بطول 75 قدم مع دي جي مباشر ووجبات راقية مميزة.", 2500.00, 10, supplier1, loc1, hut1),
            ("Traditional Arabian Coastal Seafood Feast", "مأدبة الضيافة العربية للمأكولات البحرية", "Authentic coastal dining experience with heritage dishes, live cooking, and aromatic Arabic tea.", "تجربة طعام ساحلية أصيلة تشمل أطباقاً تراثية وطهواً مباشراً وشاي بالحبق والنعناع.", 950.00, 18, supplier2, loc3, hut3),
            ("Underwater Marine Photography Workshop", "ورشة التصوير الاحترافي تحت الماء", "Professional masterclass on underwater ocean photography with top equipment provided.", "دورة احترافية متخصصة في التصوير الفوتوغرافي تحت الماء مع توفير أحدث الكاميرات والمعدات.", 1100.00, 8, supplier1, loc2, hut2),
            ("Full Moon Overwater Yoga & Meditation", "جلسة اليوجا والاسترخاء تحت اكتمال القمر", "Rejuvenating evening yoga and sound healing session on our overwater ocean deck.", "جلسة يوجا وعلاج بالصوت على المنصة الزجاجية فوق الماء تحت ضوء القمر.", 400.00, 15, supplier2, loc1, hut1),
            ("Coastal Jet Ski & Water Sports Championship", "بطولة الرياضات البحرية والدبابات المائية", "Adrenaline-fueled water sports tournament with guided jet ski safari and professional instruction.", "بطولة رياضية مشوقة تشمل جولات الدبابات المائية والرياضات البحرية الممتعة.", 750.00, 15, supplier1, loc2, hut2),
        ]

        start_d = date(2026, 1, 1)
        end_d = date(2026, 12, 31)

        for title, title_ar, desc, desc_ar, price, cap, supp, loc, hut in events_data:
            ev = Event.objects.create(
                supplier=supp,
                title=title,
                title_ar=title_ar,
                description=desc,
                description_ar=desc_ar,
                rate=4.95,
                capacity=cap,
                min_purchasable_quantity=1,
                max_purchasable_quantity=5,
                image="uploads/services/event_image/event1.jpg",
                location=loc,
                hut=hut,
                is_active=True,
                is_delete=False
            )
            EventInclude.objects.create(event=ev, icon=icon_bbq, description="Complimentary Drinks & Equipment", description_ar="مشروبات ومعدات مجانية")
            EventNote.objects.create(event=ev, description="Daily available departure", description_ar="مغادرة متاحة يومياً")

            # Attach daily available dates
            curr = start_d
            e_dates = []
            while curr <= end_d:
                e_obj, _ = AvailableDateEvent.objects.get_or_create(date=curr, defaults={'price': price, 'capacity': cap, 'is_active': True})
                e_dates.append(e_obj)
                curr += timedelta(days=1)
            ev.available_dates.set(e_dates)

        # 8. Seed Expanded Services (8 Services)
        self.stdout.write("Seeding 8+ Expanded Services...")
        services_data = [
            ("Traditional Saudi Coffee & Dates Welcome", "خدمة القهوة السعودية والتمور الفاخرة", "Freshly brewed cardamon coffee served in royal dallah with premium Madinah dates.", "قهوة سعودية بالهيل والزعفران تُقدم بالدلة الملكية مع أفخر أنواع التمور الفاخرة.", 100.00, 20, supplier2, hut1),
            ("Private Yacht Sunset Cruise", "رحلة اليخت الخاص عند الغروب", "90-minute private luxury yacht cruise around the reef islands with complimentary cold beverages.", "رحلة بياخت فاخر خاص لمدة 90 دقيقة حول جزر المرجان مع تقديم عصائر طازجة وخدمة ضيافة كاملة.", 450.00, 10, supplier1, hut2),
            ("Rustic Breakfast Platter to Room", "وجبة الإفطار الريفي الفاخر في الكوخ", "Gourmet coastal breakfast delivered hot directly to your overwater terrace every morning.", "إفطار ساحلي فاخر يُقدم ساخناً يومياً مباشرة إلى تراس الكوخ الخاص بك.", 150.00, 15, supplier2, hut3),
            ("Campfire Seafood Feast", "مأدبة المأكولات البحرية على الحطب", "Traditional wood-fired grilled lobster, hamour, and prawns served on the shore.", "استاكوزا وهامور وروبيان مشوي على الفحم والحطب يُقدم على الشاطئ مباشرة.", 300.00, 12, supplier2, hut1),
            ("24/7 Private Butler & Concierge Service", "خدمة المساعد الشخصي الخاص على مدار الساعة", "Dedicated personal butler managing all dining, spa, and sea activity reservations.", "مساعد شخصي خاص لتلبية طلباتك وتنسيق الوجبات وحجوزات السبا والأنشطة.", 500.00, 5, supplier1, hut3),
            ("In-Hut Luxury Spa & Body Massage", "خدمة المساج والاسترخاء الملكي داخل الكوخ", "60-minute relaxing aromatherapy massage delivered by certified wellness therapists inside your hut.", "جلسة مساج وعلاج بالزيوت العطرية لمدة 60 دقيقة يقدمها أخصائيون محترفون داخل كوخك.", 600.00, 8, supplier1, hut2),
            ("Executive Private Airport Chauffeur", "خدمة التوصيل الخاص السريع من وإلى المطار", "Luxury SUV transfer with private driver between King Abdulaziz Airport and Ken Reef.", "توصيل بدرجة رجال الأعمال وسيارة فاخرة وسائق خاص من وإلى المطار.", 250.00, 10, supplier2, hut1),
            ("Floating Breakfast Tray in Private Pool", "صينية الإفطار العائمة في المسبح الخاص", "Instagram-worthy floating breakfast basket served right in your private plunge pool.", "صينية إفطار عائمة فاخرة في المسبح الخاص بالكوخ التقاط أجمل الصور الذكارية.", 200.00, 10, supplier2, hut3),
        ]

        for title, title_ar, desc, desc_ar, price, cap, supp, hut in services_data:
            sv = Services.objects.create(
                supplier=supp,
                title=title,
                title_ar=title_ar,
                description=desc,
                description_ar=desc_ar,
                price=price,
                capacity=cap,
                min_purchasable_quantity=1,
                max_purchasable_quantity=5,
                is_active=True,
                is_delete=False,
                hut=hut
            )
            curr = start_d
            s_dates = []
            while curr <= end_d:
                s_obj, _ = AvailableDateService.objects.get_or_create(date=curr, defaults={'price': price, 'capacity': cap, 'is_active': True})
                s_dates.append(s_obj)
                curr += timedelta(days=1)
            sv.available_dates.set(s_dates)

        # 9. Seed Ken Special Items
        self.stdout.write("Seeding Ken Special Items...")
        item1 = KenSpecialItems.objects.create(
            supplier=supplier1,
            title="Premium Reef Snorkeling Kit",
            title_ar="طقم سنوركلينج المرجان الفاخر",
            price=120.00,
            capacity=20,
            min_purchasable_quantity=1,
            max_purchasable_quantity=5,
            is_active=True,
            is_delete=False
        )
        item1.huts.add(hut1, hut2, hut3)

        # 10. Seed Content (About Us, FAQ, Story, Terms, Reviews, Partners)
        self.stdout.write("Seeding Content, FAQs, Partners, and Reviews...")
        AboutUs.objects.create(
            about_us="Ken Luxury Reef offers an exclusive coastal sanctuary blending authentic Arabian hospitality with world-class overwater luxury and marine reef conservation.",
            about_us_ar="يوفر كِن للمرجان الفاخر ملاذاً ساحلياً استثنائياً يجمع بين أصول الضيافة العربية الأصيلة والرفاهية الفاخرة فوق مياه البحر الأحمر مع الحفاظ على البيئة البحرية.",
            vission="To be the premier sustainable overwater reef sanctuary in the Middle East.",
            vission_ar="أن نكون الملاذ الفاخر والمستدام الأول للشعب المرجانية فوق الماء في الشرق الأوسط.",
            mission="Delivering unforgettable marine luxury experiences that preserve ocean ecology while pampering every guest.",
            mission_ar="تقديم تجارب ضيافة بحرية لا تُنسى تحافظ على البيئة البحرية وتوفر أقصى درجات الرفاهية والراحة لضيوفنا."
        )

        FAQ.objects.create(
            question="What is the check-in and check-out policy?",
            question_ar="ما هي سياسة تسجيل الوصول والمغادرة؟",
            answer="Check-in starts from 2:00 PM and check-out is until 12:00 PM. Early check-in or late check-out is subject to availability.",
            answer_ar="يبدأ تسجيل الوصول من الساعة 2:00 ظهراً والمغادرة حتى الساعة 12:00 ظهراً. يمكن طلب تسجيل الوصول المبكر أو المغادرة المتأخرة حسب التوافر."
        )
        FAQ.objects.create(
            question="Are water sports and diving activities included?",
            question_ar="هل الأنشطة البحرية والغوص مشمولة مع الحجز؟",
            answer="Complimentary snorkeling equipment and kayaks are provided for all huts. Specialized scuba tours and yacht cruises can be added easily during booking.",
            answer_ar="يتم توفير معدات السنوركلينج والكاياك مجاناً لجميع الأكواخ. كما يمكن إضافة جولات الغوص المتخصصة ورحلات اليخت بسهولة أثناء الحجز."
        )
        FAQ.objects.create(
            question="What is your cancellation policy?",
            question_ar="ما هي سياسة الإلغاء؟",
            answer="Free cancellation is available up to 48 hours before check-in date with full refund.",
            answer_ar="الإلغاء المجاني متاح حتى 48 ساعة قبل موعد الوصول مع استرداد كامل المبلغ."
        )

        Story.objects.create(
            title="Conceived Over Red Sea Waves",
            title_ar="فكرة نبعت من أحضان البحر الأحمر",
            description="Founded in 2024, Ken Luxury Reef was created to rethink luxury hospitality by harmonizing eco-friendly design with pristine marine ecosystems.",
            description_ar="تأسست كِن عام 2024 لإعادة تعريف الضيافة الفاخرة من خلال التناغم التام بين التصميم الصديق للبيئة والنظم البحرية النقية."
        )

        OurService.objects.create(
            title="Overwater Sanctuary Living",
            title_ar="إقامة ملاذ فاخر فوق الماء",
            description="Bespoke overwater villas crafted from sustainable materials with glass floor ocean viewing windows.",
            description_ar="أكواخ وفلل فاخرة فوق الماء مصنوعة من مواد مستدامة ومزودة بنوافذ أرضية زجاجية لمشاهدة البحر."
        )

        SpecailAboutUs.objects.create(
            title="Private Marine Reef Butler Service / خدمة المساعد الشخصي الخاص",
            title_ar="خدمة مساعد شخصي خاص على مدار 24 ساعة لتلبية جميع احتياجاتك وتنسيق الوجبات والأنشطة."
        )

        TermsAndCindationsTitle.objects.create(
            title="Ken Luxury Reef Terms of Service",
            title_ar="الشروط والأحكام الخاصة بكِن للمرجان الفاخر"
        )

        TermsAndCindations.objects.create(
            title="Booking and Reservation Rules",
            title_ar="قواعد وإجراءات الحجز",
            description="All bookings require valid identification and full payment confirmation prior to arrival.",
            description_ar="تتطلب جميع الحجوزات إبراز هوية سارية وتأكيد الدفع الكامل قبل موعد الوصول."
        )

        Partners.objects.create(image="uploads/partner/partner1.png")
        Partners.objects.create(image="uploads/partner/partner2.png")

        HutRating.objects.create(
            user=guest1,
            hut=hut1,
            value=5.00,
            content="An absolute paradise! The Wahad Hut surpassed all our expectations. The glass floor marine view and seafood dinner were spectacular.",
            is_testmonail=True
        )
        HutRating.objects.create(
            user=guest1,
            hut=hut2,
            value=4.90,
            content="تجربة استثنائية وبحرية خيالية! كوخ ملاذ ونظافة البحر والضيافة السعودية كانت فوق الوصف.",
            is_testmonail=True
        )

        WebStore.objects.get_or_create(pk=1, defaults={'avg_rate': 4.95})
        WebStoreRating.objects.create(user=guest1, rating=5, comment="World-class luxury reef experience in Saudi Arabia!")

        # 11. Seed Sample Bookings & Dashboard Metrics
        self.stdout.write("Seeding Sample Bookings & Dashboard Metrics...")
        booking1 = Booking.objects.create(
            user=guest1,
            hut=hut1,
            total_price=2100.00,
            persons_max_num=4,
            kids_max_num=2,
            paid=2100.00,
            not_paid=0.00,
            status='paid',
            is_paid=True,
            is_qr_genereated=True,
            promocode=promo1
        )
        BookingDate.objects.create(
            booking=booking1,
            date_from=date(2026, 8, 10),
            date_to=date(2026, 8, 13),
            total_price=2100.00,
            is_paid=True,
            is_confirmed=True
        )
        EventTicket.objects.create(
            booking=booking1,
            event=Event.objects.first(),
            quantity=2,
            date=date(2026, 8, 11),
            is_paid=True,
            is_confirmed=True
        )
        ServiceTicket.objects.create(
            booking=booking1,
            service=Services.objects.first(),
            quantity=2,
            date=date(2026, 8, 10),
            is_paid=True,
            is_confirmed=True
        )

        booking2 = Booking.objects.create(
            user=guest1,
            hut=hut2,
            total_price=1000.00,
            persons_max_num=2,
            kids_max_num=1,
            paid=1000.00,
            not_paid=0.00,
            status='confirmed',
            is_paid=True,
            is_qr_genereated=True,
            promocode=promo2
        )
        BookingDate.objects.create(
            booking=booking2,
            date_from=date(2026, 8, 20),
            date_to=date(2026, 8, 21),
            total_price=1000.00,
            is_paid=True,
            is_confirmed=True
        )

        # Support & Notifications
        Support.objects.create(
            full_name="Ahmed Al-Otaibi",
            email="guest1@kenluxuryreef.com",
            operation=supplier1,
            content="Can we request a late check-out for Wahad Hut on August 13th?",
            is_replied=False
        )
        Notification.objects.create(
            user=guest1,
            content_object=booking1,
            message="Your reservation at Wahad Hut is confirmed!",
            message_ar="تم تأكيد حجزك في كوخ واحة بنجاح!",
            type="booking",
            mark_as_read=False
        )

        self.stdout.write(self.style.SUCCESS("Database successfully seeded with reverted hut titles, 8+ events, 8+ services, content, and full dashboard metrics through 2026/12/31!"))
