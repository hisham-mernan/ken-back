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
        AvailableDateRanges.objects.create(huts=hut1, date_from="2026-01-01", date_to="2026-12-31", price=5.00)
        AvailableDateRanges.objects.create(huts=hut2, date_from="2026-01-01", date_to="2026-12-31", price=5.00)
        AvailableDateRanges.objects.create(huts=hut3, date_from="2026-01-01", date_to="2026-12-31", price=5.00)

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
            ("Red Sea Sunset BBQ and Marine Gala", "حفل عشاء وشواء غروب البحر الأحمر", "An unforgettable evening featuring freshly grilled seafood, live acoustic melodies, and guided night ocean observation.", "أمسية ساحرة لا تُنسى تتضمن مأكولات بحرية طازجة ومشوية، وعزف موسيقي حاد، ومراقبة الكائنات البحرية ليلاً.", 5.00, 15, supplier1, loc1, hut1),
            ("Reef Diving and Coral Conservation Tour", "جولة الغوص واستكشاف شعب المرجان", "Guided scuba diving trip led by marine biologists exploring untouched coral reefs and rare sea turtles.", "رحلة غوص استكشافية برفقة خبراء أحياء بحرية لاستكشاف الشعب المرجانية العذراء والسلاحف البحرية النادرة.", 5.00, 12, supplier1, loc2, hut2),
            ("Stargazing Desert Shore Night", "ليلة التخييم ومراقبة النجوم على الشاطئ", "A magical night of telescope astronomy, traditional campfire tales, and traditional Saudi hospitality under the stars.", "ليلة ساحرة لرصد النجوم بالتلسكوبات، وحكايات السمر حول شبة النار والضيافة السعودية الأصيلة تحت النجوم.", 5.00, 20, supplier2, loc3, hut3),
            ("Luxury Private Yacht Party and Live DJ", "حفل يخت خاص فاخر مع دي جي", "Exclusive sunset cruise on a 75ft motor yacht with live DJ performance and gourmet catering.", "رحلة يخت فاخر عند الغروب بطول 75 قدم مع دي جي مباشر ووجبات راقية مميزة.", 5.00, 10, supplier1, loc1, hut1),
            ("Traditional Arabian Coastal Seafood Feast", "مأدبة الضيافة العربية للمأكولات البحرية", "Authentic coastal dining experience with heritage dishes, live cooking, and aromatic Arabic tea.", "تجربة طعام ساحلية أصيلة تشمل أطباقاً تراثية وطهواً مباشراً وشاي بالحبق والنعناع.", 5.00, 18, supplier2, loc3, hut3),
            ("Underwater Marine Photography Workshop", "ورشة التصوير الاحترافي تحت الماء", "Professional masterclass on underwater ocean photography with top equipment provided.", "دورة احترافية متخصصة في التصوير الفوتوغرافي تحت الماء مع توفير أحدث الكاميرات والمعدات.", 5.00, 8, supplier1, loc2, hut2),
            ("Full Moon Overwater Yoga and Meditation", "جلسة اليوجا والاسترخاء تحت اكتمال القمر", "Rejuvenating evening yoga and sound healing session on our overwater ocean deck.", "جلسة يوجا وعلاج بالصوت على المنصة الزجاجية فوق الماء تحت ضوء القمر.", 5.00, 15, supplier2, loc1, hut1),
            ("Coastal Jet Ski and Water Sports Championship", "بطولة الرياضات البحرية والدبابات المائية", "Adrenaline-fueled water sports tournament with guided jet ski safari and professional instruction.", "بطولة رياضية مشوقة تشمل جولات الدبابات المائية والرياضات البحرية الممتعة.", 5.00, 15, supplier1, loc2, hut2),
        ]

        start_d = date(2026, 1, 1)
        end_d = date(2026, 12, 31)
        all_dates = [start_d + timedelta(days=i) for i in range((end_d - start_d).days + 1)]

        AvailableDateEvent.objects.bulk_create(
            [AvailableDateEvent(date=d, price=5.00, capacity=20, is_active=True) for d in all_dates],
            ignore_conflicts=True
        )
        e_dates_qs = list(AvailableDateEvent.objects.filter(date__gte=start_d, date__lte=end_d))

        AvailableDateService.objects.bulk_create(
            [AvailableDateService(date=d, price=5.00, capacity=20, is_active=True) for d in all_dates],
            ignore_conflicts=True
        )
        s_dates_qs = list(AvailableDateService.objects.filter(date__gte=start_d, date__lte=end_d))

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
            ev.available_dates.set(e_dates_qs)

        # 8. Seed Expanded Services (8 Services)
        self.stdout.write("Seeding 8+ Expanded Services...")
        services_data = [
            ("Traditional Saudi Coffee & Dates Welcome", "خدمة القهوة السعودية والتمور الفاخرة", "Freshly brewed cardamon coffee served in royal dallah with premium Madinah dates.", "قهوة سعودية بالهيل والزعفران تُقدم بالدلة الملكية مع أفخر أنواع التمور الفاخرة.", 5.00, 20, supplier2, hut1),
            ("Private Yacht Sunset Cruise", "رحلة اليخت الخاص عند الغروب", "90-minute private luxury yacht cruise around the reef islands with complimentary cold beverages.", "رحلة بياخت فاخر خاص لمدة 90 دقيقة حول جزر المرجان مع تقديم عصائر طازجة وخدمة ضيافة كاملة.", 5.00, 10, supplier1, hut2),
            ("Rustic Breakfast Platter to Room", "وجبة الإفطار الريفي الفاخر في الكوخ", "Gourmet coastal breakfast delivered hot directly to your overwater terrace every morning.", "إفطار ساحلي فاخر يُقدم ساخناً يومياً مباشرة إلى تراس الكوخ الخاص بك.", 5.00, 15, supplier2, hut3),
            ("Campfire Seafood Feast", "مأدبة المأكولات البحرية على الحطب", "Traditional wood-fired grilled lobster, hamour, and prawns served on the shore.", "استاكوزا وهامور وروبيان مشوي على الفحم والحطب يُقدم على الشاطئ مباشرة.", 5.00, 12, supplier2, hut1),
            ("24/7 Private Butler & Concierge Service", "خدمة المساعد الشخصي الخاص على مدار الساعة", "Dedicated personal butler managing all dining, spa, and sea activity reservations.", "مساعد شخصي خاص لتلبية طلباتك وتنسيق الوجبات وحجوزات السبا والأنشطة.", 5.00, 5, supplier1, hut3),
            ("In-Hut Luxury Spa & Body Massage", "خدمة المساج والاسترخاء الملكي داخل الكوخ", "60-minute relaxing aromatherapy massage delivered by certified wellness therapists inside your hut.", "جلسة مساج وعلاج بالزيوت العطرية لمدة 60 دقيقة يقدمها أخصائيون محترفون داخل كوخك.", 5.00, 8, supplier1, hut2),
            ("Executive Private Airport Chauffeur", "خدمة التوصيل الخاص السريع من وإلى المطار", "Luxury SUV transfer with private driver between King Abdulaziz Airport and Ken Reef.", "توصيل بدرجة رجال الأعمال وسيارة فاخرة وسائق خاص من وإلى المطار.", 5.00, 10, supplier2, hut1),
            ("Floating Breakfast Tray in Private Pool", "صينية الإفطار العائمة في المسبح الخاص", "Instagram-worthy floating breakfast basket served right in your private plunge pool.", "صينية إفطار عائمة فاخرة في المسبح الخاص بالكوخ التقاط أجمل الصور الذكارية.", 5.00, 10, supplier2, hut3),
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
            sv.available_dates.set(s_dates_qs)ing all dining, spa, and sea activity reservations.", "مساعد شخصي خاص لتلبية طلباتك وتنسيق الوجبات وحجوزات السبا والأنشطة.", 5.00, 5, supplier1, hut3),
            ("In-Hut Luxury Spa & Body Massage", "خدمة المساج والاسترخاء الملكي داخل الكوخ", "60-minute relaxing aromatherapy massage delivered by certified wellness therapists inside your hut.", "جلسة مساج وعلاج بالزيوت العطرية لمدة 60 دقيقة يقدمها أخصائيون محترفون داخل كوخك.", 5.00, 8, supplier1, hut2),
            ("Executive Private Airport Chauffeur", "خدمة التوصيل الخاص السريع من وإلى المطار", "Luxury SUV transfer with private driver between King Abdulaziz Airport and Ken Reef.", "توصيل بدرجة رجال الأعمال وسيارة فاخرة وسائق خاص من وإلى المطار.", 5.00, 10, supplier2, hut1),
            ("Floating Breakfast Tray in Private Pool", "صينية الإفطار العائمة في المسبح الخاص", "Instagram-worthy floating breakfast basket served right in your private plunge pool.", "صينية إفطار عائمة فاخرة في المسبح الخاص بالكوخ التقاط أجمل الصور الذكارية.", 5.00, 10, supplier2, hut3),
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
            price=5.00,
            capacity=20,
            min_purchasable_quantity=1,
            max_purchasable_quantity=5,
            is_active=True,
            is_delete=False
        )
        item1.huts.add(hut1, hut2, hut3)

        # 10. Seed Content (About Us, FAQ, Story, Terms, Reviews, Partners)
        self.stdout.write("Seeding Content, FAQs, Partners, and Official PDF Terms...")
        AboutUs.objects.create(
            about_us="Over 40 years ago, this land was simply a vast space filled with cherished memories, carrying within it family stories and grandfathers' gatherings beneath the shade of trees. It belonged to our father, who cared for every inch of it over the decades. One day, he gave us the choice, saying: 'Do with it whatever you see fit.' From here, the idea of building tourist huts was born—reflecting nature's simplicity and warm hospitality, serving as a peaceful sanctuary for anyone seeking tranquility, beauty, and an authentic experience surrounded by nature.",
            about_us_ar="قبل أكثر من 40 عامًا، كانت هذه الأرض مجرد مساحة واسعة مليئة بالذكريات، تحمل في طياتها قصص العائلة واجتماعات الأجداد تحت ظلال الأشجار. كانت ملكًا لوالدنا، الذي اعتنى بها طوال عقود، محبًا لكل شبر فيها، مترددًا في التخلي عنها رغم تغير الأزمان. وفي يوم من الأيام، قرر أن يمنحنا الخيار، قائلاً: \"افعلوا بها ما ترونه مناسبًا.\" من هنا، ولدت فكرة بناء أكواخ سياحية، تعكس بساطة الطبيعة ودفء الضيافة، لتكون ملاذًا لكل من يبحث عن الهدوء، والجمال، والتجربة الأصيلة وسط الطبيعة.",
            vission="To be the first choice and trusted reference in designing and crafting countryside huts.",
            vission_ar="أن نكون الخيار الأول والمرجع الموثوق في تصميم وبناء الأكواخ الريفية.",
            mission="Preserving the spirit of the land and its family heritage in every detail while delivering uncompromised quality, natural harmony, and authentic Saudi hospitality.",
            mission_ar="نحافظ على روح الأرض وتاريخها العائلي في كل تفصيلة، ونلتزم بتقديم خدمات راقية، الجودة والتميز، التناغم مع الطبيعة، والأصالة والضيافة."
        )

        # 12 Official Bilingual FAQs
        faqs_list = [
            (
                "Is there a swimming pool?",
                "هل يوجد مسبح ؟",
                "No, the huts are designed as a peaceful sanctuary surrounded by nature, without a swimming pool.",
                "لا، الأكواخ مصممة كملاذ هادئ بين الطبيعة، بدون مسبح."
            ),
            (
                "Are there services near the huts?",
                "هل يوجد خدمات حول الأكواخ ؟",
                "Yes, nearby you will find restaurants, cafes, grocery stores, and tourist activities in Al Hada. The location is pinned via QR code for easy navigation.",
                "نعم، حوالينا مطاعم، مقاهي، بقالات، وأنشطة سياحية في الهدا، والموقع محدد بالباركود لتسهيل الوصول."
            ),
            (
                "Do you have special booking offers?",
                "هل لديكم عروض على الحجوزات؟",
                "Yes, we offer seasonal discounts and special packages during holidays. Follow us on Instagram to discover our latest offers.",
                "نعم، نقدم عروض موسمية وخاصة بالأعياد والعطلات – تابعونا على الإنستقرام لمعرفة أحدثها ."
            ),
            (
                "What about cleanliness and hygiene?",
                "عن نظافة المكان؟",
                "Cleanliness is our top priority. Every hut is thoroughly cleaned, sanitized, and inspected after each stay.",
                "النظافة أولوية أساسية عندنا، وكل كوخ يتم تنظيفه وتعقيمه بعد كل إقامة بشكل كامل."
            ),
            (
                "What is the difference between the three huts?",
                "مالفرق بين الثلاثة أكواخ؟",
                "* Small Hut: Ideal for 2 guests.\n* Medium Hut: Suitable for small families (3–4 guests).\n* Large Hut: Perfect for families or groups (6–8 guests).",
                "* الكوخ الصغير: مناسب لشخصين.\n* الكوخ الوسط: مناسب لعائلة صغيرة (3–4 أشخاص).\n* الكوخ الكبير: مناسب للعوائل أو المجموعات ( 6-8) أشخاص."
            ),
            (
                "Can I book a half-night stay?",
                "أقدر أخذ نص ليلة؟",
                "Yes, half-night bookings are available.",
                "نعم، يوجد حجز نص ليلة."
            ),
            (
                "Is drinking water provided?",
                "هل يوجد مياه شرب ؟",
                "Yes, both drinking water and fresh utility water are provided.",
                "نعم، متوفر مياه شرب + مياه للاستعمال."
            ),
            (
                "Are cooking utensils available?",
                "هل يوجد أدوات طبخ ؟",
                "Basic cooking utensils and a barbecue grill are provided (you are welcome to bring your personal items if preferred).",
                "متوفر أدوات أساسية للطبخ + شواية (ممكن تضيفون أدواتكم الخاصة لو تحبون)."
            ),
            (
                "Is the access road paved?",
                "الطريق معبد ولا لا؟",
                "Yes, the road is fully paved and clear all the way to the huts.",
                "نعم، الطريق معبد وواضح حتى الوصول لموقع الأكواخ."
            ),
            (
                "Do you offer event decoration and party coordination?",
                "يوجد تنسيق حفلات؟",
                "We offer simple party setup services (birthdays, anniversaries, small celebrations) and collaborate with expert event partners for larger custom requests.",
                "نوفر خدمة تنسيق بسيطة للحفلات (عيد ميلاد – ذكرى – مناسبات صغيرة)، وبالتعاون مع شركاء تنسيق لو تبغون خيارات أكبر."
            ),
            (
                "Are loud speakers or sound amplifiers allowed?",
                "السماعة أو المكبر مسموح ولا ممنوع؟",
                "Large loudspeakers are strictly prohibited to preserve the tranquility of nature and comfort of other guests.",
                "ممنوع استخدام السماعات الكبيرة حفاظًا على هدوء المكان وراحة الضيوف الآخرين."
            ),
            (
                "How many bedrooms are in each hut?",
                "كم عدد الغرف في كل كوخ ؟",
                "* Small Hut: 1 Bedroom\n* Medium Hut: 2 Bedrooms\n* Large Hut: 4 Bedrooms",
                "الصغير غرفة نوم واحدة \nالوسط غرفتين \nالكبير أربعة غرف"
            )
        ]

        for q_en, q_ar, a_en, a_ar in faqs_list:
            FAQ.objects.create(
                question=q_en,
                question_ar=q_ar,
                answer=a_en,
                answer_ar=a_ar
            )

        Story.objects.create(
            title="The Story of Ken: 40 Years of Heritage",
            title_ar="عن كِن - حكاية أرض وذكريات 40 عاماً",
            description="Over 40 years ago, this land was simply a vast space filled with cherished memories, carrying within it family stories and grandfathers' gatherings beneath the shade of trees. It belonged to our father, who cared for every inch of it over the decades. One day, he gave us the choice, saying: 'Do with it whatever you see fit.' From here, the idea of building tourist huts was born—reflecting nature's simplicity and warm hospitality.",
            description_ar="قبل أكثر من 40 عامًا، كانت هذه الأرض مجرد مساحة واسعة مليئة بالذكريات، تحمل في طياتها قصص العائلة واجتماعات الأجداد تحت ظلال الأشجار. كانت ملكًا لوالدنا، الذي اعتنى بها طوال عقود، محبًا لكل شبر فيها، مترددًا في التخلي عنها رغم تغير الأزمان. وفي يوم من الأيام، قرر أن يمنحنا الخيار، قائلاً: \"افعلوا بها ما ترونه مناسبًا.\" من هنا، ولدت فكرة بناء أكواخ سياحية، تعكس بساطة الطبيعة ودفء الضيافة، لتكون ملاذًا لكل من يبحث عن الهدوء، والجمال، والتجربة الأصيلة وسط الطبيعة."
        )

        OurService.objects.create(
            title="Natural Wood Craftsmanship / خشب طبيعي وبناء سعودي",
            title_ar="خشب طبيعي وبناء بأيدي سعودية",
            description="High-grade natural wood structures built by Saudi hands in strategic scenic locations with smart keyless entry.",
            description_ar="أكواخ مصممة بخشب طبيعي فاخر وبُنيت بأيدي سعودية في مواقع استراتيجية مميزة ومزودة بنظام الدخول الذكي."
        )

        SpecailAboutUs.objects.create(
            title="What Sets Ken Apart / ما يميّز أكواخ كِن",
            title_ar="خشب طبيعي - دخول ذكي - بُني بأيدي سعودية - موقع استراتيجي - تجربة كوخ فاخرة"
        )

        # Official Terms and Conditions Extracted from PDF Document
        TermsAndCindationsTitle.objects.create(
            title="General Terms and Conditions for Booking Ken Huts",
            title_ar="الشروط والأحكام العامة لحجز أكواخ كِن"
        )

        TermsAndCindations.objects.create(
            title="Guest Responsibility for Damages and Losses",
            title_ar="مسؤولية الضيف عن التلفيات والخسائر",
            description="The guest assumes full responsibility for any material damages or losses occurring inside the hut or its facilities during the stay, whether intentional or resulting from misuse or negligence. In the event of property damage, Ken Huts management reserves the right to claim appropriate compensation based on repair or replacement costs. If payment is refused, management reserves the right to take legal action through competent authorities.",
            description_ar="يتحمل الضيف كامل المسؤولية عن أي تلفيات أو خسائر مادية تحدث داخل الكوخ أو في مرافقه أثناء فترة الإقامة، سواء كانت متعمدة أو ناتجة عن سوء استخدام أو إهمال. في حال حدوث أي ضرر بالممتلكات، يحق لإدارة أكواخ كن المطالبة بالتعويض المناسب وفقاً لتكلفة الإصلاح أو الاستبدال. في حال رفض سداد التعويض، يحق للإدارة اتخاذ الإجراءات النظامية اللازمة عبر الجهات المختصة."
        )

        TermsAndCindations.objects.create(
            title="Cancellation and Amendment Policy",
            title_ar="سياسة الإلغاء والتعديل",
            description="Reservations can be cancelled with a full refund within (14) business days if cancelled 24 hours or more before check-in. If cancelled less than 24 hours before check-in, 50% of the total booking amount will be deducted. In case of a no-show without prior notice, the full booking value may be charged.",
            description_ar="يمكن إلغاء الحجز مع استرداد كامل المبلغ خلال (14) يوم عمل إذا تم الإلغاء قبل موعد الدخول بـ 24 ساعة أو أكثر. في حال تم الإلغاء قبل موعد الدخول بأقل من 24 ساعة، يتم خصم 50% من إجمالي مبلغ الحجز. في حال عدم الحضور دون إشعار مسبق، قد يتم احتساب قيمة الحجز كاملة."
        )

        TermsAndCindations.objects.create(
            title="Adherence to Facility Usage",
            title_ar="الالتزام باستخدام المرافق",
            description="Using the huts for any illegal activities or actions violating public order and morality is strictly prohibited. Moving furniture or changing electrical appliance locations without prior management approval is forbidden. Guests must maintain cleanliness, use facilities responsibly, and leave the hut in proper condition upon departure.",
            description_ar="يُمنع استخدام الأكواخ لأي أنشطة غير مشروعة أو مخالفة للأنظمة والآداب العامة. يُمنع نقل الأثاث أو تغيير مواقع الأجهزة الكهربائية دون موافقة مسبقة من الإدارة. يلتزم الضيوف بالحفاظ على نظافة المكان واستخدام المرافق بشكل مسؤول، وإعادة الكوخ بالحالة المناسبة عند المغادرة."
        )

        TermsAndCindations.objects.create(
            title="Guest and Visitor Capacity",
            title_ar="عدد الضيوف والزوار",
            description="Guests must adhere to the guest capacity specified in the reservation. If welcoming additional visitors is desired, prior coordination and approval from management is required. Management reserves the right to deny entry to any additional visitors exceeding the hut's maximum capacity.",
            description_ar="يجب الالتزام بعدد الضيوف المحدد في الحجز. في حال الرغبة باستقبال زوار إضافيين، يجب التنسيق المسبق مع الإدارة وأخذ الموافقة. تحتفظ الإدارة بحق رفض دخول أي عدد إضافي في حال تجاوز الطاقة الاستيعابية للكوخ."
        )

        TermsAndCindations.objects.create(
            title="Quiet Hours and Privacy Respect",
            title_ar="الالتزام بالهدوء واحترام الخصوصية",
            description="At Ken Huts, we strive to provide a quiet, comfortable environment for all guests. Please maintain an appropriate noise level and avoid disturbing others. Respect the privacy of fellow guests and surrounding properties.",
            description_ar="نحرص في أكواخ كن على توفير بيئة هادئة ومريحة لجميع الضيوف، لذا نرجو الالتزام بمستوى صوت مناسب وعدم إزعاج الآخرين. يُرجى احترام خصوصية الضيوف الآخرين والممتلكات المحيطة."
        )

        TermsAndCindations.objects.create(
            title="Management Rights",
            title_ar="أحقية الإدارة",
            description="Ken Huts management reserves the right to cancel any reservation if false information is provided or terms are violated. Management also holds the right to terminate a stay in the event of non-compliance with rules or property damage.",
            description_ar="تحتفظ إدارة أكواخ كن بالحق في إلغاء أي حجز في حال تقديم معلومات غير صحيحة أو مخالفة الشروط. كما يحق للإدارة إنهاء الإقامة في حال عدم الالتزام بالأنظمة أو الإضرار بالممتلكات."
        )

        TermsAndCindations.objects.create(
            title="Personal Belongings Liability",
            title_ar="المسؤولية الشخصية",
            description="Ken Huts management is not liable for any loss, theft, or damage to personal belongings of guests during their stay.",
            description_ar="إدارة أكواخ كن غير مسؤولة عن فقدان أو تلف أي ممتلكات شخصية للضيوف أثناء فترة الإقامة."
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
