from django.contrib import admin
from .models import *

# Register all models
admin.site.register(AvailableDateEvent)
admin.site.register(AvailableDateService)
admin.site.register(AvailableDateRanges)
admin.site.register(PromoCode)

admin.site.register(HutIncludes)
admin.site.register(HutImages)
admin.site.register(Location)
admin.site.register(Note)
admin.site.register(Hut)
admin.site.register(Event)
admin.site.register(KenSpecialItems)
admin.site.register(Services)
admin.site.register(HutRating)

admin.site.register(Booking)
admin.site.register(BookingDate)
admin.site.register(EventTicket)
admin.site.register(ServiceTicket)
admin.site.register(SpecialItemTicket)
admin.site.register(Icon)
admin.site.register(HutActivity)
admin.site.register(HutMainService)
admin.site.register(EventInclude)
admin.site.register(EventNote)
admin.site.register(QrLogs)
