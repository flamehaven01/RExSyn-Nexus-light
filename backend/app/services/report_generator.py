"""
Academic Report Generator for RExSyn Nexus
===========================================

Generates publication-quality PDF reports for structure prediction results.
Professional academic tone with comprehensive metrics, graphs, and tables.

Dependencies:
- reportlab >= 4.0
- matplotlib >= 3.8
- Pillow >= 10.0
"""

import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import tempfile
import base64

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        PageBreak,
        Image,
        KeepTogether,
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    # Minimal stubs to avoid import errors in test environments without reportlab
    class ParagraphStyle:  # type: ignore
        def __init__(self, *args, **kwargs):
            ...

    def getSampleStyleSheet():  # type: ignore
        return {}

    def SimpleDocTemplate(*args, **kwargs):  # type: ignore
        return None

    def Paragraph(*args, **kwargs):  # type: ignore
        return None

    def Spacer(*args, **kwargs):  # type: ignore
        return None

    def Table(*args, **kwargs):  # type: ignore
        return None

    def TableStyle(*args, **kwargs):  # type: ignore
        return None

    def PageBreak(*args, **kwargs):  # type: ignore
        return None

    def Image(*args, **kwargs):  # type: ignore
        return None

    def KeepTogether(*args, **kwargs):  # type: ignore
        return None
    print("WARNING: reportlab not installed. PDF generation unavailable.")

try:
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("WARNING: matplotlib not installed. Graph generation unavailable.")

import numpy as np


class AcademicReportGenerator:
    """
    Generates professional academic reports for structure prediction results.

    Report structure:
    1. Title page with metadata
    2. Executive summary
    3. Methods and parameters
    4. Results and quality metrics
    5. Structural analysis with graphs
    6. Ethics certification
    7. References and appendices
    """

    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab is required for PDF generation")

        self.page_width, self.page_height = A4
        self.styles = self._create_styles()

    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """Create academic document styles."""
        styles = getSampleStyleSheet()

        # Title style
        styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        ))

        # Subtitle style
        styles.add(ParagraphStyle(
            name='Subtitle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica',
        ))

        # Section heading
        styles.add(ParagraphStyle(
            name='SectionHeading',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold',
            borderWidth=0,
            borderPadding=0,
            leftIndent=0,
        ))

        # Subsection heading
        styles.add(ParagraphStyle(
            name='SubsectionHeading',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#333333'),
            spaceAfter=10,
            spaceBefore=14,
            fontName='Helvetica-Bold',
        ))

        # Academic body text
        styles.add(ParagraphStyle(
            name='AcademicBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#333333'),
            alignment=TA_JUSTIFY,
            spaceAfter=12,
            fontName='Helvetica',
        ))

        # Code/data style
        styles.add(ParagraphStyle(
            name='Code',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#1e40af'),
            fontName='Courier',
            leftIndent=20,
            spaceAfter=10,
            backColor=colors.HexColor('#f3f4f6'),
        ))

        return styles

    def generate_report(
        self,
        job_id: str,
        result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Generate comprehensive academic report.

        Args:
            job_id: Unique job identifier
            result: Prediction results dictionary
            metadata: Additional metadata
            output_path: Output PDF path (temp file if None)

        Returns:
            Path to generated PDF
        """
        if output_path is None:
            fd, output_path = tempfile.mkstemp(suffix='.pdf', prefix=f'report_{job_id}_')
            output_path = Path(output_path)

        # Create PDF document
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Build document content
        story = []

        # 1. Title page
        story.extend(self._build_title_page(job_id, result, metadata))
        story.append(PageBreak())

        # 2. Executive summary
        story.extend(self._build_executive_summary(result))
        story.append(Spacer(1, 0.3 * inch))

        # 3. Methods
        story.extend(self._build_methods_section(result, metadata))
        story.append(Spacer(1, 0.3 * inch))

        # 4. Results and metrics
        story.extend(self._build_results_section(result))
        story.append(PageBreak())

        # 5. Quality assessment tables
        story.extend(self._build_quality_tables(result))
        story.append(Spacer(1, 0.3 * inch))

        # 6. Ethics certification
        story.extend(self._build_ethics_section(result))
        story.append(PageBreak())

        # 7. Conclusions
        story.extend(self._build_conclusions(result))

        # Build PDF
        doc.build(story, onFirstPage=self._add_header_footer, onLaterPages=self._add_header_footer)

        return output_path

    def _build_title_page(self, job_id: str, result: Dict, metadata: Optional[Dict]) -> List:
        """Build title page."""
        elements = []

        # Title
        elements.append(Spacer(1, 1.5 * inch))
        elements.append(Paragraph(
            "Structure Prediction Analysis Report",
            self.styles['ReportTitle']
        ))

        # Subtitle
        quality_grade = result.get('quality_grade', 'N/A')
        elements.append(Paragraph(
            f"Quality Grade: {quality_grade}",
            self.styles['Subtitle']
        ))

        elements.append(Spacer(1, 0.5 * inch))

        # Metadata table
        meta_data = [
            ['Job ID:', job_id],
            ['Date Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')],
            ['Prediction Method:', result.get('method', 'N/A')],
            ['Processing Time:', f"{result.get('processing_time_seconds', 0):.1f} seconds"],
            ['SIDRCE Validated:', 'Yes' if result.get('ethics_certification') else 'No'],
        ]

        if metadata:
            if 'experiment_type' in metadata:
                meta_data.append(['Experiment Type:', metadata['experiment_type']])
            if 'research_purpose' in metadata:
                meta_data.append(['Research Purpose:', metadata['research_purpose']])

        meta_table = Table(meta_data, colWidths=[2.5*inch, 3.5*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e5e5')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(meta_table)
        elements.append(Spacer(1, 1 * inch))

        # Watermark
        elements.append(Paragraph(
            "Generated by RExSyn Nexus v0.4.0 | Ethics-Certified BioAI Platform",
            self.styles['Subtitle']
        ))

        return elements

    def _build_executive_summary(self, result: Dict) -> List:
        """Build executive summary section."""
        elements = []

        elements.append(Paragraph("1. Executive Summary", self.styles['SectionHeading']))

        confidence = result.get('confidence', 0) * 100
        grade = result.get('quality_grade', 'N/A')

        summary_text = f"""
        This report presents a comprehensive analysis of the structure prediction performed
        with quality grade <b>{grade}</b> and overall confidence of <b>{confidence:.1f}%</b>.
        The prediction was validated through the SIDRCE (Semantic Intent Drift and Responsible
        Computational Ethics) pipeline, ensuring compliance with ethical AI standards.
        """

        if result.get('md_refinement_applied'):
            summary_text += """
            Molecular dynamics refinement was applied to optimize structural geometry and
            minimize potential energy artifacts.
            """

        if result.get('ethics_certification'):
            ove_score = result['ethics_certification'].get('ove_score', 0)
            summary_text += f"""
            The structure achieved an OVE' (Output Validation Ethics) score of
            <b>{ove_score:.3f}</b>, indicating {self._interpret_ove_score(ove_score)}.
            """

        elements.append(Paragraph(summary_text, self.styles['AcademicBody']))

        return elements

    def _build_methods_section(self, result: Dict, metadata: Optional[Dict]) -> List:
        """Build methods section."""
        elements = []

        elements.append(Paragraph("2. Methods and Computational Parameters", self.styles['SectionHeading']))

        method = result.get('method', 'Unknown')
        methods_text = f"""
        <b>2.1 Prediction Algorithm:</b> The structure was predicted using {method},
        a state-of-the-art deep learning model for protein structure prediction.
        The algorithm leverages evolutionary information, multiple sequence alignments,
        and geometric constraints to generate high-accuracy structural models.
        """

        elements.append(Paragraph(methods_text, self.styles['AcademicBody']))

        if metadata:
            params_text = f"""
            <b>2.2 Computational Parameters:</b>
            Confidence threshold: {metadata.get('confidence_threshold', 0.75):.2f}.
            SAXS validation: {'Enabled' if metadata.get('saxs_validation') else 'Disabled'}.
            Automatic MD refinement: {'Enabled' if metadata.get('md_refinement_auto') else 'Disabled'}.
            """
            elements.append(Paragraph(params_text, self.styles['AcademicBody']))

        return elements

    def _build_results_section(self, result: Dict) -> List:
        """Build results section with metrics."""
        elements = []

        elements.append(Paragraph("3. Results and Quality Metrics", self.styles['SectionHeading']))

        # Primary metrics
        confidence = result.get('confidence', 0) * 100
        plddt = result.get('plddt_score', 0)

        results_text = f"""
        <b>3.1 Structural Confidence:</b> The predicted structure achieved an overall
        confidence score of {confidence:.1f}%, with a mean pLDDT (predicted Local Distance
        Difference Test) score of {plddt:.1f}. pLDDT scores above 70 indicate high-confidence
        regions, while scores below 50 suggest disordered or low-confidence segments.
        """

        elements.append(Paragraph(results_text, self.styles['AcademicBody']))

        # SAXS validation
        if result.get('saxs_chi2') is not None:
            saxs_text = f"""
            <b>3.2 SAXS Validation:</b> Small-angle X-ray scattering validation yielded a
            χ² value of {result['saxs_chi2']:.2f}, indicating
            {self._interpret_saxs_chi2(result['saxs_chi2'])}.
            """
            elements.append(Paragraph(saxs_text, self.styles['AcademicBody']))

        # DockQ score
        if result.get('dockq_score') is not None:
            dockq_text = f"""
            <b>3.3 Docking Quality:</b> The DockQ score of {result['dockq_score']:.2f}
            indicates {self._interpret_dockq(result['dockq_score'])} docking quality.
            """
            elements.append(Paragraph(dockq_text, self.styles['AcademicBody']))

        return elements

    def _build_quality_tables(self, result: Dict) -> List:
        """Build quality assessment tables."""
        elements = []

        elements.append(Paragraph("4. Quality Assessment", self.styles['SectionHeading']))

        # Main metrics table
        metrics_data = [
            ['Metric', 'Value', 'Interpretation'],
            ['Overall Confidence', f"{result.get('confidence', 0)*100:.1f}%", self._interpret_confidence(result.get('confidence', 0))],
            ['pLDDT Score', f"{result.get('plddt_score', 0):.1f}", self._interpret_plddt(result.get('plddt_score', 0))],
            ['Quality Grade', result.get('quality_grade', 'N/A'), self._interpret_grade(result.get('quality_grade', 'F'))],
        ]

        if result.get('saxs_chi2') is not None:
            metrics_data.append(['SAXS χ²', f"{result['saxs_chi2']:.2f}", self._interpret_saxs_chi2(result['saxs_chi2'])])

        if result.get('dockq_score') is not None:
            metrics_data.append(['DockQ Score', f"{result['dockq_score']:.2f}", self._interpret_dockq(result['dockq_score'])])

        metrics_table = Table(metrics_data, colWidths=[2*inch, 1.5*inch, 3*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a1a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(metrics_table)

        # PoseBusters validation if available
        if result.get('posebuster_checks'):
            elements.append(Spacer(1, 0.3 * inch))
            elements.append(Paragraph("4.1 PoseBusters Geometric Validation", self.styles['SubsectionHeading']))

            pb_data = [['Check', 'Status']]
            for check, passed in result['posebuster_checks'].items():
                check_name = check.replace('_', ' ').title()
                status = '✓ Pass' if passed else '✗ Fail'
                pb_data.append([check_name, status])

            pb_table = Table(pb_data, colWidths=[4*inch, 2.5*inch])
            pb_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8b5cf6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))

            elements.append(pb_table)

        return elements

    def _build_ethics_section(self, result: Dict) -> List:
        """Build ethics certification section."""
        elements = []

        elements.append(Paragraph("5. SIDRCE Ethics Certification", self.styles['SectionHeading']))

        if not result.get('ethics_certification'):
            elements.append(Paragraph(
                "Ethics certification data not available for this prediction.",
                self.styles['AcademicBody']
            ))
            return elements

        cert = result['ethics_certification']
        ove_score = cert.get('ove_score', 0)
        drift_status = cert.get('drift_status', 'Unknown')
        policy = cert.get('policy_compliance', 'Unknown')

        ethics_text = f"""
        The prediction underwent comprehensive ethical validation through the SIDRCE
        (Semantic Intent Drift and Responsible Computational Ethics) framework.
        This seven-stage pipeline ensures responsible AI usage and output validation.

        <b>5.1 OVE' Score:</b> The Output Validation Ethics (OVE') score of {ove_score:.3f}
        {self._interpret_ove_score(ove_score)}. Scores above 0.85 indicate high ethical
        compliance and output integrity.

        <b>5.2 Drift Detection:</b> LLM drift check status: <b>{drift_status}</b>.
        This validation ensures the model output remains aligned with training distribution
        and intended use cases.

        <b>5.3 Policy Compliance:</b> Policy check result: <b>{policy}</b>.
        All predictions are validated against institutional ethics guidelines and
        research integrity standards.
        """

        elements.append(Paragraph(ethics_text, self.styles['AcademicBody']))

        return elements

    def _build_conclusions(self, result: Dict) -> List:
        """Build conclusions section."""
        elements = []

        elements.append(Paragraph("6. Conclusions and Recommendations", self.styles['SectionHeading']))

        grade = result.get('quality_grade', 'F')
        confidence = result.get('confidence', 0) * 100

        if grade in ['S', 'A']:
            conclusion = f"""
            The predicted structure demonstrates exceptional quality (Grade {grade}) with
            {confidence:.1f}% confidence. The model is suitable for immediate use in
            downstream applications including drug design, molecular docking, and functional
            analysis. Publication-quality structural data has been achieved.
            """
        elif grade == 'B':
            conclusion = f"""
            The prediction achieved good quality (Grade {grade}) with {confidence:.1f}%
            confidence. While suitable for most analytical purposes, careful review of
            low-confidence regions is recommended. Consider targeted MD refinement of
            specific domains if higher precision is required.
            """
        elif grade == 'C':
            conclusion = f"""
            The structure shows acceptable quality (Grade {grade}) with {confidence:.1f}%
            confidence. Significant review and validation are recommended before use in
            critical applications. Additional experimental validation (e.g., crystallography,
            NMR, cryo-EM) would strengthen confidence in structural features.
            """
        else:
            conclusion = f"""
            The prediction quality (Grade {grade}, {confidence:.1f}% confidence) falls below
            recommended thresholds for most applications. Consider rerunning with alternative
            methods, adjusted parameters, or additional sequence information. Experimental
            structure determination is strongly recommended.
            """

        elements.append(Paragraph(conclusion, self.styles['AcademicBody']))

        # Recommendations
        recommendations = []

        if result.get('md_refinement_applied'):
            recommendations.append("MD refinement has been applied successfully.")
        else:
            recommendations.append("Consider applying MD refinement for improved geometric quality.")

        if result.get('saxs_chi2', 100) > 5.0:
            recommendations.append("High SAXS χ² indicates potential discrepancies with solution state. Consider ensemble modeling.")

        if result.get('ethics_certification', {}).get('ove_score', 0) < 0.90:
            recommendations.append("Review ethics validation results for potential concerns.")

        if recommendations:
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph("<b>Recommendations:</b>", self.styles['AcademicBody']))
            for rec in recommendations:
                elements.append(Paragraph(f"• {rec}", self.styles['AcademicBody']))

        return elements

    def _add_header_footer(self, canvas_obj, doc):
        """Add header and footer to pages."""
        canvas_obj.saveState()

        # Footer
        footer_text = f"RExSyn Nexus v0.4.0 | Generated {datetime.now().strftime('%Y-%m-%d')} | Page {doc.page}"
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.setFillColor(colors.HexColor('#999999'))
        canvas_obj.drawCentredString(self.page_width / 2, 0.5 * inch, footer_text)

        # Header line
        canvas_obj.setStrokeColor(colors.HexColor('#e5e5e5'))
        canvas_obj.setLineWidth(0.5)
        canvas_obj.line(72, self.page_height - 60, self.page_width - 72, self.page_height - 60)

        canvas_obj.restoreState()

    # Interpretation helpers
    def _interpret_confidence(self, conf: float) -> str:
        if conf >= 0.9: return "Excellent"
        if conf >= 0.8: return "High"
        if conf >= 0.7: return "Moderate"
        return "Low"

    def _interpret_plddt(self, score: float) -> str:
        if score >= 90: return "Very high confidence"
        if score >= 70: return "Confident"
        if score >= 50: return "Low confidence"
        return "Very low confidence"

    def _interpret_grade(self, grade: str) -> str:
        grades = {
            'S': 'Exceptional - Publication ready',
            'A': 'High quality - Minor refinements beneficial',
            'B': 'Good - Review recommended',
            'C': 'Acceptable - Significant review needed',
            'D': 'Marginal - Consider rerunning',
            'F': 'Failed - Investigation required'
        }
        return grades.get(grade, 'Unknown')

    def _interpret_saxs_chi2(self, chi2: float) -> str:
        if chi2 < 2.0: return "excellent agreement with experimental data"
        if chi2 < 5.0: return "good agreement with minor discrepancies"
        return "significant discrepancies requiring investigation"

    def _interpret_dockq(self, score: float) -> str:
        if score >= 0.8: return "high"
        if score >= 0.5: return "medium"
        if score >= 0.23: return "acceptable"
        return "incorrect"

    def _interpret_ove_score(self, score: float) -> str:
        if score >= 0.95: return "exceptional ethical compliance"
        if score >= 0.90: return "excellent ethical validation"
        if score >= 0.85: return "satisfactory ethical standards"
        return "requires ethical review"


# Convenience function
def generate_academic_report(
    job_id: str,
    result: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate academic report PDF.

    Args:
        job_id: Job identifier
        result: Prediction results
        metadata: Optional metadata
        output_path: Output path (temp file if None)

    Returns:
        Path to generated PDF
    """
    generator = AcademicReportGenerator()
    return generator.generate_report(job_id, result, metadata, output_path)
