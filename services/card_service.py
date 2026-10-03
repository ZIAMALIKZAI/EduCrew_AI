import io
import zipfile
import hmac
import hashlib
import os
import pandas as pd
from PIL import Image, ImageDraw
import qrcode

HMAC_SECRET = os.getenv("EDUCREW_SIGNING_SECRET", "educrew_pk_gov_sec_2026").encode()

class IDCardService:
    @classmethod
    def sign_payload(cls, raw_data: str) -> str:
        """Generates HMAC-SHA256 signature for Pakistani Institutional Cards."""
        return hmac.new(HMAC_SECRET, raw_data.encode(), hashlib.sha256).hexdigest()[:12]

    # ---------------- 1. STUDENT OFFICIAL CARD (PAKISTANI SYSTEM) ----------------
    @classmethod
    def create_student_card(
        cls,
        admission_no: str,
        roll_no: str,
        student_name: str,
        father_name: str,
        class_name: str,
        section: str = "A",
        blood_group: str = "B+",
        emergency_contact: str = "+92 300 0000000",
        school_name: str = "GOVERNMENT HIGH SCHOOL",
        school_phone: str = "+92 91 1234567",
        school_email: str = "info@school.edu.pk"
    ) -> Image.Image:
        """
        Renders an authentic, professional Pakistani Student ID Card (600x980 px).
        Supports Nursery, KG, Prep, Class 1 to Class 10/12.
        """
        width, height = 600, 980
        card = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(card)

        # Header - Emerald/Green standard for Student Badges
        draw.rectangle([(0, 0), (width, 150)], fill="#065F46")
        draw.rectangle([(0, 150), (width, 160)], fill="#F59E0B")  # Gold ribbon

        draw.text((width // 2, 45), school_name.upper(), fill="#FFFFFF", anchor="mm")
        draw.text((width // 2, 85), "STUDENT IDENTITY CARD", fill="#D1FAE5", anchor="mm")
        draw.text((width // 2, 120), "ACADEMIC SESSION: 2026 - 2027", fill="#FDE68A", anchor="mm")

        # Student Avatar Placeholder
        center_x = width // 2
        avatar_y = 250
        radius = 70
        draw.ellipse([(center_x - radius - 4, avatar_y - radius - 4), (center_x + radius + 4, avatar_y + radius + 4)], fill="#F59E0B")
        draw.ellipse([(center_x - radius, avatar_y - radius), (center_x + radius, avatar_y + radius)], fill="#E2E8F0")
        draw.ellipse([(center_x - 28, avatar_y - 40), (center_x + 28, avatar_y + 10)], fill="#94A3B8")
        draw.chord([(center_x - 50, avatar_y - 5), (center_x + 50, avatar_y + 65)], 0, 180, fill="#94A3B8")

        # Class & Section Pill Badge
        badge_text = f"STUDENT • {class_name.upper()} ({section.upper()})"
        draw.rounded_rectangle([(center_x - 160, 345), (center_x + 160, 380)], radius=17, fill="#065F46")
        draw.text((center_x, 362), badge_text, fill="#FFFFFF", anchor="mm")

        # Student Name
        draw.text((center_x, 415), student_name.upper(), fill="#0F172A", anchor="mm")

        # Student Academic Data Grid
        box_top = 450
        draw.rounded_rectangle([(35, box_top), (width - 35, box_top + 185)], radius=12, fill="#F8FAFC", outline="#E2E8F0", width=2)

        fields = [
            ("Father's Name :", father_name.title()),
            ("Admission No   :", admission_no),
            ("Class Roll No  :", str(roll_no)),
            ("Blood Group    :", blood_group),
            ("Emergency Call :", emergency_contact)
        ]

        y_offset = box_top + 22
        for label, val in fields:
            draw.text((55, y_offset), label, fill="#64748B")
            val_color = "#DC2626" if "Blood" in label else "#0F172A"
            draw.text((220, y_offset), str(val), fill=val_color)
            y_offset += 32

        # Signed QR Code (Encodes: STU|AdmissionNo|Name|Class|RollNo|Contact)
        raw_body = f"STU|{admission_no}|{student_name}|{class_name}|{roll_no}|{emergency_contact}"
        sig = cls.sign_payload(raw_body)
        signed_token = f"{raw_body}#{sig}"

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
        qr.add_data(signed_token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#065F46", back_color="white").convert("RGB").resize((150, 150))
        card.paste(qr_img, (center_x - 75, 660))

        draw.text((center_x, 825), "SCAN AT CAMPUS GATE FOR DAILY ATTENDANCE", fill="#64748B", anchor="mm")

        # Official School Contact Footer
        draw.rectangle([(0, 860), (width, height)], fill="#0F172A")
        draw.text((center_x, 888), f"School Phone: {school_phone} | Email: {school_email}", fill="#E2E8F0", anchor="mm")
        draw.text((center_x, 920), "PROPERTY OF INSTITUTION - IF FOUND RETURN TO PRINCIPAL OFFICE", fill="#94A3B8", anchor="mm")
        draw.text((center_x, 948), f"HMAC Verified Token: {sig}", fill="#38BDF8", anchor="mm")

        return card

    # ---------------- 2. TEACHER / STAFF CARD (PAKISTANI SYSTEM) ----------------
    @classmethod
    def create_staff_card(
        cls,
        emp_id: str,
        staff_name: str,
        designation: str,
        bps_scale: str,
        department: str,
        cnic_no: str,
        official_email: str,
        mobile_no: str,
        emergency_contact: str,
        blood_group: str = "O+",
        institution_name: str = "GOVERNMENT HIGH SCHOOL",
        school_phone: str = "+92 91 1234567"
    ) -> Image.Image:
        """
        Renders an authentic, professional Pakistani Faculty & Staff ID Card (600x980 px).
        Tailored for: PST, EST, SST, Subject Specialist, Farm Master, Principal, Lab Incharge.
        """
        width, height = 600, 980
        card = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(card)

        # Header - Deep Navy Blue for Faculty/Staff
        draw.rectangle([(0, 0), (width, 150)], fill="#1E3A8A")
        draw.rectangle([(0, 150), (width, 160)], fill="#F59E0B")  # Gold accent

        draw.text((width // 2, 45), institution_name.upper(), fill="#FFFFFF", anchor="mm")
        draw.text((width // 2, 85), "FACULTY & OFFICIAL STAFF CARD", fill="#DBEAFE", anchor="mm")
        draw.text((width // 2, 120), "EDUCATION & LITERACY DEPARTMENT", fill="#FDE68A", anchor="mm")

        # Staff Avatar Circle
        center_x = width // 2
        avatar_y = 250
        radius = 70
        draw.ellipse([(center_x - radius - 4, avatar_y - radius - 4), (center_x + radius + 4, avatar_y + radius + 4)], fill="#F59E0B")
        draw.ellipse([(center_x - radius, avatar_y - radius), (center_x + radius, avatar_y + radius)], fill="#E2E8F0")
        draw.ellipse([(center_x - 28, avatar_y - 40), (center_x + 28, avatar_y + 10)], fill="#1E3A8A")
        draw.chord([(center_x - 50, avatar_y - 5), (center_x + 50, avatar_y + 65)], 0, 180, fill="#1E3A8A")

        # Designation & BPS Badge Chip
        chip_text = f"{designation.upper()} (BPS-{bps_scale})"
        draw.rounded_rectangle([(center_x - 175, 345), (center_x + 175, 380)], radius=17, fill="#1E3A8A")
        draw.text((center_x, 362), chip_text, fill="#FFFFFF", anchor="mm")

        # Staff Name
        draw.text((center_x, 415), staff_name.upper(), fill="#0F172A", anchor="mm")

        # Staff Official Data Grid
        box_top = 445
        draw.rounded_rectangle([(35, box_top), (width - 35, box_top + 205)], radius=12, fill="#F8FAFC", outline="#E2E8F0", width=2)

        staff_fields = [
            ("Personal / Emp ID :", emp_id),
            ("Department / Cadre:", department),
            ("CNIC Number       :", cnic_no),
            ("Official Email    :", official_email),
            ("Official Phone    :", mobile_no),
            ("Emergency Contact :", emergency_contact),
            ("Blood Group       :", blood_group)
        ]

        y_offset = box_top + 18
        for label, val in staff_fields:
            draw.text((50, y_offset), label, fill="#64748B")
            val_color = "#DC2626" if "Blood" in label else "#0F172A"
            draw.text((230, y_offset), str(val), fill=val_color)
            y_offset += 26

        # Signed QR Code (Encodes: STAFF|EmpID|Name|Designation|BPS|Phone)
        raw_body = f"STAFF|{emp_id}|{staff_name}|{designation}|{department}|{mobile_no}"
        sig = cls.sign_payload(raw_body)
        signed_token = f"{raw_body}#{sig}"

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
        qr.add_data(signed_token)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="#1E3A8A", back_color="white").convert("RGB").resize((135, 135))
        card.paste(qr_img, (center_x - 67, 675))

        draw.text((center_x, 830), "AUTHENTICATED FACULTY ATTENDANCE TOKEN", fill="#64748B", anchor="mm")

        # Footer
        draw.rectangle([(0, 860), (width, height)], fill="#0F172A")
        draw.text((center_x, 888), f"School Gate Desk: {school_phone} | Authorized Authority Signature", fill="#E2E8F0", anchor="mm")
        draw.text((center_x, 920), "OFFICIAL GOVERNMENT PROPERTY - VALID FOR CAMPUS ACCESS", fill="#94A3B8", anchor="mm")
        draw.text((center_x, 948), f"HMAC Verified Digital Token: {sig}", fill="#38BDF8", anchor="mm")

        return card

    # ---------------- 3. BULK ZIP GENERATION ----------------
    @classmethod
    def generate_bulk_student_cards_zip(cls, df: pd.DataFrame, school_name: str, school_phone: str, school_email: str) -> bytes:
        col_map = {str(c).strip().lower(): c for c in df.columns}
        
        adm_col = next((col_map[c] for c in col_map if "admission" in c or "adm" in c or "id" in c), None)
        roll_col = next((col_map[c] for c in col_map if "roll" in c), None)
        name_col = next((col_map[c] for c in col_map if "student" in c or "name" in c), None)
        father_col = next((col_map[c] for c in col_map if "father" in c), None)
        class_col = next((col_map[c] for c in col_map if "class" in c or "grade" in c), None)
        sec_col = next((col_map[c] for c in col_map if "sec" in c), None)
        blood_col = next((col_map[c] for c in col_map if "blood" in c), None)
        emg_col = next((col_map[c] for c in col_map if "emergency" in c or "contact" in c or "phone" in c), None)

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for idx, r in df.iterrows():
                adm = str(r[adm_col]).strip() if adm_col else f"ADM-{idx+1001}"
                roll = str(r[roll_col]).strip() if roll_col else f"{idx+1}"
                name = str(r[name_col]).strip() if name_col else f"Student_{idx+1}"
                father = str(r[father_col]).strip() if father_col else "Guardian"
                c_name = str(r[class_col]).strip() if class_col else "Class 10th"
                sec = str(r[sec_col]).strip() if sec_col else "A"
                bld = str(r[blood_col]).strip() if blood_col and pd.notna(r[blood_col]) else "B+"
                emg = str(r[emg_col]).strip() if emg_col and pd.notna(r[emg_col]) else "+92 300 0000000"

                card = cls.create_student_card(
                    admission_no=adm,
                    roll_no=roll,
                    student_name=name,
                    father_name=father,
                    class_name=c_name,
                    section=sec,
                    blood_group=bld,
                    emergency_contact=emg,
                    school_name=school_name,
                    school_phone=school_phone,
                    school_email=school_email
                )
                b = io.BytesIO()
                card.save(b, format="PNG")
                safe_name = "".join(c for c in f"{c_name}_{roll}_{name}" if c.isalnum() or c in (' ', '_', '-')).rstrip()
                z.writestr(f"{safe_name}.png", b.getvalue())

        zip_buf.seek(0)
        return zip_buf.getvalue()

    @classmethod
    def generate_bulk_staff_cards_zip(cls, df: pd.DataFrame, school_name: str, school_phone: str) -> bytes:
        col_map = {str(c).strip().lower(): c for c in df.columns}

        id_col = next((col_map[c] for c in col_map if "emp" in c or "id" in c or "personal" in c), None)
        name_col = next((col_map[c] for c in col_map if "name" in c or "teacher" in c), None)
        desig_col = next((col_map[c] for c in col_map if "desig" in c or "post" in c or "role" in c), None)
        bps_col = next((col_map[c] for c in col_map if "bps" in c or "scale" in c or "grade" in c), None)
        dept_col = next((col_map[c] for c in col_map if "dept" in c or "subject" in c), None)
        cnic_col = next((col_map[c] for c in col_map if "cnic" in c), None)
        email_col = next((col_map[c] for c in col_map if "email" in c), None)
        phone_col = next((col_map[c] for c in col_map if "phone" in c or "mobile" in c), None)
        emg_col = next((col_map[c] for c in col_map if "emergency" in c), None)
        blood_col = next((col_map[c] for c in col_map if "blood" in c), None)

        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
            for idx, r in df.iterrows():
                e_id = str(r[id_col]).strip() if id_col else f"EMP-{idx+501}"
                t_name = str(r[name_col]).strip() if name_col else f"Teacher_{idx+1}"
                desig = str(r[desig_col]).strip() if desig_col else "Subject Specialist"
                bps = str(r[bps_col]).strip() if bps_col else "17"
                dept = str(r[dept_col]).strip() if dept_col else "Academics"
                cnic = str(r[cnic_col]).strip() if cnic_col else "17301-0000000-0"
                email = str(r[email_col]).strip() if email_col else f"staff{idx+1}@school.edu.pk"
                phone = str(r[phone_col]).strip() if phone_col else "+92 300 0000000"
                emg = str(r[emg_col]).strip() if emg_col and pd.notna(r[emg_col]) else "+92 301 0000000"
                blood = str(r[blood_col]).strip() if blood_col and pd.notna(r[blood_col]) else "O+"

                card = cls.create_staff_card(
                    emp_id=e_id,
                    staff_name=t_name,
                    designation=desig,
                    bps_scale=bps,
                    department=dept,
                    cnic_no=cnic,
                    official_email=email,
                    mobile_no=phone,
                    emergency_contact=emg,
                    blood_group=blood,
                    institution_name=school_name,
                    school_phone=school_phone
                )
                b = io.BytesIO()
                card.save(b, format="PNG")
                safe_name = "".join(c for c in f"{desig}_{t_name}" if c.isalnum() or c in (' ', '_', '-')).rstrip()
                z.writestr(f"{safe_name}.png", b.getvalue())

        zip_buf.seek(0)
        return zip_buf.getvalue()
