from pathlib import Path

import docx
from docx.shared import Pt, Inches
from fpdf import FPDF


def create_resume_docx(
    user_details: dict,
    summary: str,
    experience: list[dict],
    projects: list[dict],
    skills: list[str],
    certificates: list[dict],
    max_bullets_per_section: int = 3,
):
    try:
        # =============================== DOCX =============================
        doc = docx.Document()

        # 0.5-inch margins
        sec = doc.sections[0]
        for side in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
            setattr(sec, side, Inches(0.5))

        # base fonts
        doc.styles["Heading 1"].font.size, doc.styles["Heading 1"].font.bold = Pt(12), True
        doc.styles["Heading 2"].font.size, doc.styles["Heading 2"].font.bold = Pt(11), True
        doc.styles["Normal"].font.size = Pt(10)

        # bullet paragraph style
        bullet_style = doc.styles.add_style("BulletTiny", docx.enum.style.WD_STYLE_TYPE.PARAGRAPH)
        bullet_style.paragraph_format.left_indent = Inches(0.2)
        bullet_style.paragraph_format.space_after = Pt(0)
        bullet_style.font.size = Pt(10)

        # header
        doc.add_heading(user_details["name"], 0)
        doc.paragraphs[-1].runs[0].font.size = Pt(14)
        doc.add_paragraph(
            f"{user_details['email']} | {user_details['phone_number']} | {user_details['address']}"
        )

        # summary
        doc.add_heading("SUMMARY", 1)
        doc.add_paragraph(summary, style="Normal")

        # experience
        doc.add_heading("EXPERIENCE", 1)
        for role in experience:
            doc.add_heading(role["company"], 2)
            doc.add_paragraph(f"{role['role']} | {role['dates']}", style="Normal")
            for i, line in enumerate(role["achievements"].splitlines()):
                if i >= max_bullets_per_section:
                    break
                if line.strip():
                    doc.add_paragraph(f"• {line.strip()}", style="BulletTiny")

        # projects
        doc.add_heading("PROJECTS", 1)
        for p in projects[:max_bullets_per_section]:
            doc.add_heading(p["name"], 2)
            doc.add_paragraph(f"{p['description']} | {p['technologies']}", style="Normal")

        # skills
        doc.add_heading("SKILLS", 1)
        doc.add_paragraph(", ".join(skills), style="Normal")

        # certificates
        if certificates:
            doc.add_heading("CERTIFICATES", 1)
            for c in certificates[:max_bullets_per_section]:
                doc.add_heading(c["name"], 2)
                doc.add_paragraph(c["description"], style="Normal")

        # save DOCX
        out_dir = Path("resume")
        out_dir.mkdir(exist_ok=True)
        docx_path = out_dir / "new_resume.docx"
        doc.save(docx_path)
        print("✔ DOCX saved →", docx_path)

    except Exception as e:
        print(f"⚠ Failed to create DOCX resume: {e}")
        # optional: log the exception properly if you want
