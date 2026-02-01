from django.core.management.base import BaseCommand
from django.conf import settings
from apps.pos.models import POSDevice


class Command(BaseCommand):
    help = "List one absolute URL per POS device"

    def handle(self, *args, **options):
        devices = POSDevice.objects.select_related('branch', 'branch__tenant').all()
        for d in devices:
            # Prefer persisted public_url
            if d.public_url:
                self.stdout.write(d.public_url)
                continue

            tenant = getattr(d, 'tenant', None) or (getattr(d.branch, 'tenant', None) if d.branch else None)
            tenant_domain = getattr(tenant, 'domain', None) if tenant else None
            path = d.get_absolute_url() or ''

            if tenant_domain:
                if tenant_domain.startswith('http://') or tenant_domain.startswith('https://'):
                    base = tenant_domain.rstrip('/')
                else:
                    base = f"https://{tenant_domain}".rstrip('/')
                public = base + path if path.startswith('/') else base + '/' + path
            else:
                site_url = getattr(settings, 'SITE_URL', '') or ''
                if site_url:
                    base = site_url.rstrip('/')
                    public = base + path if path.startswith('/') else base + '/' + path
                else:
                    public = path

            # Normalize duplicate slashes but keep protocol intact
            public = public.replace('://', 'PROTOCOL_TEMP')
            while '//' in public:
                public = public.replace('//', '/')
            public = public.replace('PROTOCOL_TEMP', '://')

            self.stdout.write(public)
