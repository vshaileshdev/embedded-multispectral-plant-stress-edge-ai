import io
import json
from fpdf import FPDF
from datetime import datetime

class ProgressReportPDF(FPDF):
    def __init__(self, plant_id, species, records, interpretation_map, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.plant_id = plant_id
        self.species = species
        # sort chronologically by experimental day/timestamp
        self.records = sorted(records, key=lambda x: x.measurement_timestamp)
        self.interpretation_map = interpretation_map
        
    def header(self):
        # Header Box
        self.set_fill_color(90, 130, 82)
        self.rect(0, 0, 210, 30, 'F')
        
        # Title
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'Plant Health Progress Report', border=0, new_x='LMARGIN', new_y='NEXT', align='C')
        self.ln(10)
            
    def footer(self):
        self.set_y(-25)
        
        self.set_fill_color(240, 240, 240)
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(200, 50, 50)
        self.cell(0, 5, "SCIENTIFIC LIMITATION NOTICE:", new_x='LMARGIN', new_y='NEXT')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 4, "Model confidence indicates statistical classification probability. It does NOT represent biological severity. Potential effects are condition-associated and not directly measured traits.", fill=True)

    def generate(self):
        self.add_page()
        self.set_text_color(0, 0, 0)
        
        # 1. Report Info
        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, f"Plant: {self.species.capitalize()}", new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 8, f"Plant ID: {self.plant_id}", new_x='LMARGIN', new_y='NEXT')
        self.cell(0, 8, f"Date generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x='LMARGIN', new_y='NEXT')
        self.ln(5)

        # 2. Measurement Timeline
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(90, 130, 82)
        self.cell(0, 10, '1. Measurement Timeline', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', '', 10)

        # Draw Table Header
        self.set_fill_color(220, 230, 220)
        self.set_font('Helvetica', 'B', 10)
        self.cell(30, 8, 'Exp. Day', border=1, fill=True)
        self.cell(50, 8, 'Date/Time', border=1, fill=True)
        self.cell(70, 8, 'Diagnosis', border=1, fill=True)
        self.cell(30, 8, 'Confidence', border=1, fill=True, new_x='LMARGIN', new_y='NEXT')

        self.set_font('Helvetica', '', 10)
        for r in self.records:
            d = r.measurement_timestamp.strftime('%Y-%m-%d %H:%M')
            conf = f"{(r.model_confidence*100):.1f}%"
            self.cell(30, 8, r.experimental_day or 'Unknown', border=1)
            self.cell(50, 8, d, border=1)
            self.cell(70, 8, r.diagnosis, border=1)
            self.cell(30, 8, conf, border=1, new_x='LMARGIN', new_y='NEXT')
        
        self.ln(5)

        # 3. Spectral Progression (ΔFeature)
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(90, 130, 82)
        self.cell(0, 10, '2. Spectral Progression (Measured feature change)', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0, 0, 0)
        
        if len(self.records) > 1:
            self.set_font('Helvetica', 'B', 10)
            self.cell(30, 8, 'Feature', border=1, fill=True)
            for i in range(1, len(self.records)):
                self.cell(40, 8, f"{self.records[i-1].experimental_day} -> {self.records[i].experimental_day}", border=1, fill=True)
            self.cell(0, 8, '', new_x='LMARGIN', new_y='NEXT')

            self.set_font('Helvetica', '', 10)
            track_features = ["NDVI", "GNDVI", "NDRE", "WBI"]
            
            for feat in track_features:
                self.cell(30, 8, feat, border=1)
                for i in range(1, len(self.records)):
                    prev = self._get_feat(self.records[i-1], feat)
                    curr = self._get_feat(self.records[i], feat)
                    if prev is not None and curr is not None:
                        delta = curr - prev
                        self.cell(40, 8, f"{delta:+.4f}", border=1)
                    else:
                        self.cell(40, 8, "N/A", border=1)
                self.cell(0, 8, '', new_x='LMARGIN', new_y='NEXT')
        else:
            self.set_font('Helvetica', 'I', 10)
            self.cell(0, 8, "Need at least two measurements to calculate progression.", new_x='LMARGIN', new_y='NEXT')
        
        self.ln(5)

        # 4. Classification Progression
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(90, 130, 82)
        self.cell(0, 10, '3. Classification Progression', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', '', 10)

        for r in self.records:
            self.set_font('Helvetica', 'B', 11)
            self.cell(0, 6, f"{r.experimental_day or 'Unknown'}: {r.diagnosis}", new_x='LMARGIN', new_y='NEXT')
            self.set_font('Helvetica', '', 10)
            
            probs = {}
            try:
                if r.class_probabilities_json:
                    probs = json.loads(r.class_probabilities_json)
            except: pass
            
            if probs:
                p_str = " | ".join([f"{k}: {(v*100):.1f}%" for k,v in probs.items()])
                self.cell(0, 5, p_str, new_x='LMARGIN', new_y='NEXT')
            self.ln(2)
        
        self.ln(5)

        # 5. Potential Effects
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(90, 130, 82)
        self.cell(0, 10, '4. Potential Biological Effects', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', 'I', 10)
        self.multi_cell(0, 5, "These are potential effects associated with the detected stress conditions across the timeline. They are not direct measurements.")
        self.set_font('Helvetica', '', 10)
        
        seen_effects = set()
        for r in self.records:
            mapping = self._get_map(r.diagnosis)
            for eff in mapping.get("potential_effects", []):
                seen_effects.add(eff)
                
        if seen_effects:
            for eff in seen_effects:
                self.cell(0, 6, f"- {eff}", new_x='LMARGIN', new_y='NEXT')
        self.ln(5)

        # 6. Recommendation Progression
        self.set_font('Helvetica', 'B', 14)
        self.set_text_color(90, 130, 82)
        self.cell(0, 10, '5. Recommendation Progression', new_x='LMARGIN', new_y='NEXT')
        self.set_text_color(0, 0, 0)
        self.set_font('Helvetica', '', 10)

        for r in self.records:
            mapping = self._get_map(r.diagnosis)
            self.set_font('Helvetica', 'B', 10)
            self.cell(0, 6, f"{r.experimental_day}:", new_x='LMARGIN', new_y='NEXT')
            self.set_font('Helvetica', '', 10)
            self.multi_cell(0, 5, mapping.get('recommendation', 'N/A'))
            self.ln(2)

        self.ln(5)

        # 7. Plant Management Summary
        if self.records:
            latest = self.records[-1]
            mapping = self._get_map(latest.diagnosis)
            
            self.set_font('Helvetica', 'B', 14)
            self.set_text_color(90, 130, 82)
            self.cell(0, 10, '6. Plant Management Summary', new_x='LMARGIN', new_y='NEXT')
            self.set_text_color(0, 0, 0)
            self.set_font('Helvetica', '', 11)
            
            self.cell(0, 6, f"Latest Measurement: {latest.diagnosis}", new_x='LMARGIN', new_y='NEXT')
            self.cell(0, 6, f"Model Confidence: {(latest.model_confidence*100):.1f}%", new_x='LMARGIN', new_y='NEXT')
            
            if "Healthy" in latest.diagnosis or "Control" in latest.diagnosis:
                self.multi_cell(0, 6, "Under the current measurement conditions, the classifier assigned the spectrum to the control class. Maintaining adequate water and nutrient conditions can support normal vegetative development and photosynthetic function.")
            else:
                self.multi_cell(0, 6, f"Recommended Next Action: {mapping.get('recommendation', 'N/A')}")
            
            # Trend language
            if len(self.records) > 1:
                first = self.records[0]
                if first.diagnosis != latest.diagnosis:
                    self.ln(2)
                    self.multi_cell(0, 6, f"Observed Trend: Across the available measurements, the classifier changed from {first.diagnosis} to {latest.diagnosis}.")
                    
        return self.output(dest='S')
        
    def _get_map(self, diagnosis):
        for key, val in self.interpretation_map.items():
            if val["diagnosis"] == diagnosis:
                return val
        return {"potential_effects": [], "recommendation": ""}
        
    def _get_feat(self, record, feat_name):
        try:
            if record.features_json:
                features = json.loads(record.features_json)
                return features.get(feat_name)
        except: pass
        return None
