import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timezone

def render_templates():
    base_dir = os.getcwd()
    templates_dir = os.path.join(base_dir, "public", "templates")
    preview_dir = os.path.join(base_dir, "preview_emails")
    os.makedirs(preview_dir, exist_ok=True)
    
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    templates = [
        {
            "name": "email/otp_email",
            "filename": "otp_email.html",
            "vars": {
                "otp_code": "123456",
                "app_logo_url": "https://res.cloudinary.com/looprail/image/upload/v1771897579/logo_full_yvbl5f.svg"
            }
        },
        {
            "name": "email/login_alert",
            "filename": "login_alert.html",
            "vars": {
                "user_first_name": "user",
                "login_time": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
                "ip_address": "192.168.1.1",
                "location": "Lagos, Lagos State, Nigeria",
                "app_logo_url": "https://res.cloudinary.com/looprail/image/upload/v1771897579/logo_full_yvbl5f.svg"
            }
        },
        {
            "name": "email/deposit_confirmed",
            "filename": "deposit_confirmed.html",
            "vars": {
                "amount": "5,000.00",
                "currency": "NGN",
                "transaction_id": "txn_abcdef123456",
                "app_logo_url": "https://res.cloudinary.com/looprail/image/upload/v1771897579/logo_full_yvbl5f.svg"
            }
        },
        {
            "name": "email/withdrawal_processed",
            "filename": "withdrawal_processed.html",
            "vars": {
                "amount": "2,500.00",
                "currency": "NGN",
                "transaction_id": "txn_7890xyz",
                "app_logo_url": "https://res.cloudinary.com/looprail/image/upload/v1771897579/logo_full_yvbl5f.svg"
            }
        }
    ]

    for t in templates:
        print(f"Rendering {t['name']}...")
        template = env.get_template(f"{t['name']}.html")
        html = template.render(**t['vars'])
        
        output_path = os.path.join(preview_dir, t['filename'])
        with open(output_path, "w") as f:
            f.write(html)
        print(f"Saved to {output_path}")

if __name__ == "__main__":
    render_templates()
