import io
import zipfile
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import qrcode
import hmac
import hashlib
import os

HMAC_SECRET = os.getenv("EDUCREW_SIGNING_SECRET", "educrew_enterprise_secure_salt_2026").encode()

class IDCardService:
    @classmethod
    def sign_payload(cls, raw_data: str) -> str:
        """Signs card token with HMAC-SHA256."""
        return hmac.new(HMAC_SECRET, raw_data.encode(), hashlib.sha256).hexdigest()[:12]

    @classmethod
    def create_official_id_card(
        cls,
        person_id: str,
        name: str,
        role: str,
        department_or_class: str,
        blood_group: str = "O+",
        emergency_contact: str = "+92 300 0000000",
        institution_name: str = "GOVERNMENT HIGH SCHOOL"
    ) -> Image.Image:
        """
        Renders a high-resolution, official vertical institutional ID card (600x950 px).
        """
        width, height = 600, 950
        card = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(card)

        # Header background banner
        header_color = "#1E3A8A" if "teacher" in role.lower() or "farm" in role.lower() or "principal" in role.lower() else "#0F766E"
        draw.rectangle([(0, 0), (width, 160)], fill=header_color)
        draw.rectangle([(0, 160), (width, 172)], fill="#F59E0B")  # Gold accent divider

        # Institution Title & Subtitle
        draw.text((width // 2, 50), institution_name, fill="#FFFFFF", anchor="mm")
        draw.text((width // 2, 95), "OFFICIAL IDENTITY CREDENTIAL", fill="#CBD5E1", anchor="mm")
        draw.text((width // 2, 130), "ACADEMIC SESSION 2026 - 2027", fill="#FDE68A", anchor="mm")

        # Avatar placeholder circle
        center_x = width // 2
        avatar_y = 265
        radius = 75
        draw.ellipse([(center_x - radius - 4, avatar_y - radius - 4), (center_x + radius + 4, avatar_y + radius + 4)], fill="#F59E0B")
        draw.ellipse([(center_x - radius, avatar_y - radius), (center_x + radius, avatar_y + radius)], fill="#E2E8F0")
        
        # Silhouette icon inside avatar
        draw.ellipse([(center_x - 30, avatar_y - 45), (center_x + 30, avatar_y + 10)], fill="#94A3B8")
        draw.chord([(center_x - 55, avatar_y - 5), (center_x + 55, avatar_y + 70)], 0, 180, fill="#94A3B8")

        # Role Badge Chip
        chip_w, chip_h = 240, 36
        chip_y = 370
        draw.rounded_rectangle(
            [(center_x - chip_w // 2, chip_y), (center_x + chip_w // 2, chip_y + chip_h)],
            radius=18,
            fill=header_color
        )
        draw.text((center_x, chip_y + chip_h // 2), role.upper(), fill="#FFFFFF", anchor="mm")

        # Name & Identifier
        draw.text((center_x, 435), name.upper(), fill="#0F172A", anchor="mm")
        draw.text((center_x, 465), f"ID / ROLL NO: {person_id}", fill="#475569", anchor="mm")

        # Data Grid Box
        box_top = 500
        draw.rounded_rectangle([(40, box_top), (width - 40, box_top + 120)], radius=10, fill="#F8FAFC", outline="#E2E8F0", width=2)
        
        # Details inside Grid Box
        draw.text((60, box_top + 30), f"Class / Dept :", fill="#64748B")
        draw.text((220, box_top + 30), f"{department_or_class}", fill="#0F172A")

        draw.text((60, box_top + 60), f"Blood Group  :", fill="#64748B")
        draw.text((220, box_top + 60), f"{blood_group}", fill="#DC2626")

        draw.text((60, box_top + 90), f"Emergency No :", fill="#64748B")
        draw.text((220, box_top + 90), f"{emergency_contact}", fill="#0F172A")

        # Cryptographic Signed QR Code Generation
        raw_body = f"{person_id.strip()}|{name.strip()}|{role.strip()}|{department_or_class.strip()}"
        signature = cls.sign_payload(raw_body)
        signed_token = f"{raw_body}#{signature}"

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=5, border=2)
        qr.add_data(signed_token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#0F172A", back_color="white").convert("RGB")
        qr_img = qr_img.resize((175, 175))

        card.paste(qr_img, (center_x - 87, 650))
        draw.text((center_x, 835), "SCAN FOR AUTOMATED GATE VERIFICATION", fill="#64748B", anchor="mm")

        # Footer
        draw.rectangle([(0, 875), (width, height)], fill="#0F172A")
        draw.text((center_x, 905), "PROPERTY OF INSTITUTION - IF FOUND RETURN TO ADMIN", fill="#94A3B8", anchor="mm")
        draw.text((center_x, 925), f"Digital Signature: {signature} | Validated", fill="#38BDF8", anchor="mm")

        return card

    @classmethod
    def generate_bulk_cards_zip(cls, df: pd.DataFrame, institution_name: str) -> bytes:
        """Parses bulk roster and generates official ID card image files in a zip."""
        col_map = {str(c).strip().lower(): c for c in df.columns}
        id_col = next((col_map[c] for c in col_map if "id" in c or "roll" in c), None)
        name_col = next((col_map[c] for c in col_map if "name" in c), None)
        role_col = next((col_map[c] for c in col_map if "role" in c or "designation" in c), None)
        class_col = next((col_map[c] for c in col_map if "class" in c or "grade" in c or "dept" in c), None)
        blood_col = next((col_map[c] for c in col_map if "blood" in c), None)
        phone_col = next((col_map[c] for c in col_map if "phone" in c or "contact" in c or "emergency" in c), None)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, row in df.iterrows():
                p_id = str(row[id_col]).strip() if id_col else f"ID_{idx+1}"
                p_name = str(row[name_col]).strip() if name_col else f"Person_{idx+1}"
                p_role = str(row[role_col]).strip() if role_col else "Student"
                p_class = str(row[class_col]).strip() if class_col else "Class 10th"
                p_blood = str(row[blood_col]).strip() if blood_col and pd.notna(row[blood_col]) else "O+"
                p_phone = str(row[phone_col]).strip() if phone_col and pd.notna(row[phone_col]) else "+92 300 0000000"

                card_img = cls.create_official_id_card(
                    person_id=p_id,
                    name=p_name,
                    role=p_role,
                    department_or_class=p_class,
                    blood_group=p_blood,
                    emergency_contact=p_phone,
                    institution_name=institution_name
                )
                img_bytes = io.BytesIO()
                card_img.save(img_bytes, format="PNG")
                
                safe_name = "".join(c for c in f"{p_id}_{p_name}_IDCard" if c.isalnum() or c in (' ', '_', '-')).rstrip()
                zip_file.writestr(f"{safe_name}.png", img_bytes.getvalue())

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
