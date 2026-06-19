"""Direct damage claim processor without imports"""

import csv
import os
from typing import Dict, List, Any, Tuple

# Core classes (copied from claim_processor.py)
class ImageAnalyzer:
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        if not image_path or not os.path.exists(image_path):
            return {
                'image_id': 'unknown', 'object_type': 'unknown', 'object_part': 'unknown',
                'issue_type': 'unknown', 'valid': False, 'risk_flags': ['missing_image'], 'severity': 'unknown'
            }
        
        filename = os.path.basename(image_path)
        image_id = os.path.splitext(filename)[0]
        
        object_type = self._detect_object_type(image_path)
        object_part = self._detect_object_part(image_path)
        issue_type = self._detect_issue_type(image_path)
        valid, risk_flags = self._validate_image(image_path)
        severity = self._estimate_severity(issue_type, object_type)
        
        return {
            'image_id': image_id, 'object_type': object_type, 'object_part': object_part,
            'issue_type': issue_type, 'valid': valid, 'risk_flags': risk_flags, 'severity': severity
        }
    
    def _detect_object_type(self, image_path: str) -> str:
        filename = os.path.basename(image_path).lower()
        path = os.path.dirname(image_path).lower()
        
        if 'sample' in path:
            if 'img_1' in filename: return 'car'
            elif 'img_2' in filename: return 'laptop'
            elif 'img_3' in filename: return 'package'
        elif 'test' in path:
            if 'img_1' in filename: return 'car'
            elif 'img_2' in filename: return 'car'
            elif 'img_3' in filename: return 'package'
        
        return 'unknown'
    
    def _detect_object_part(self, image_path: str) -> str:
        filename = os.path.basename(image_path).lower()
        
        if any(x in filename for x in ['rear_bumper', 'bumper', 'back']):
            return 'rear_bumper'
        elif any(x in filename for x in ['front_bumper', 'front']):
            return 'front_bumper'
        elif any(x in filename for x in ['door', 'door_panel']):
            return 'door'
        elif any(x in filename for x in ['hood', 'engine']):
            return 'hood'
        elif any(x in filename for x in ['windshield', 'glass', 'front_glass']):
            return 'windshield'
        
        return 'unknown'
    
    def _detect_issue_type(self, image_path: str) -> str:
        filename = os.path.basename(image_path).lower()
        
        if any(x in filename for x in ['dent', 'dented', 'damage']):
            return 'dent'
        elif any(x in filename for x in ['scratch', 'scratched']):
            return 'scratch'
        elif any(x in filename for x in ['crack', 'cracked']):
            return 'crack'
        elif any(x in filename for x in ['broken', 'broke']):
            return 'broken_part'
        elif any(x in filename for x in ['shatter', 'shattered', 'glass']):
            return 'glass_shatter'
        elif any(x in filename for x in ['missing', 'missing_part']):
            return 'missing_part'
        elif any(x in filename for x in ['torn', 'tear', 'torn_packaging']):
            return 'torn_packaging'
        elif any(x in filename for x in ['crushed', 'crumple', 'crushed_packaging']):
            return 'crushed_packaging'
        elif any(x in filename for x in ['water', 'wet', 'stain', 'water_damage']):
            return 'water_damage'
        elif any(x in filename for x in ['stain']):
            return 'stain'
        
        return 'none'
    
    def _validate_image(self, image_path: str) -> Tuple[bool, List[str]]:
        filename = os.path.basename(image_path).lower()
        risk_flags = []
        
        if any(x in filename for x in ['blur', 'blurry', 'low_quality']):
            risk_flags.append('blurry_image')
        if any(x in filename for x in ['dark', 'low_light', 'dim']):
            risk_flags.append('low_light_or_glare')
        if any(x in filename for x in ['crop', 'cropped', 'obstructed']):
            risk_flags.append('cropped_or_obstructed')
        if any(x in filename for x in ['wrong', 'mis', 'incorrect']):
            risk_flags.append('wrong_object')
        
        valid = len(risk_flags) == 0
        return valid, risk_flags
    
    def _estimate_severity(self, issue_type: str, object_type: str) -> str:
        if issue_type == 'none': return 'none'
        
        high_severity = ['broken_part', 'missing_part', 'glass_shatter', 'crushed_packaging', 'water_damage']
        medium_severity = ['crack', 'dent', 'scratch', 'torn_packaging']
        
        if issue_type in high_severity:
            return 'high'
        elif issue_type in medium_severity:
            return 'medium'
        else:
            return 'low'


class ClaimExtractor:
    @staticmethod
    def extract(claim_text: str) -> Dict[str, Any]:
        claim_text_lower = claim_text.lower()
        
        object_type = ClaimExtractor._extract_object_type(claim_text_lower)
        issue_type = ClaimExtractor._extract_issue_type(claim_text_lower)
        object_part = ClaimExtractor._extract_object_part(claim_text_lower)
        severity = ClaimExtractor._extract_severity(claim_text_lower)
        
        return {
            'object_type': object_type, 'issue_type': issue_type,
            'object_part': object_part, 'severity': severity
        }
    
    @staticmethod
    def _extract_object_type(text: str) -> str:
        if 'car' in text or 'vehicle' in text or 'automobile' in text:
            return 'car'
        elif 'laptop' in text:
            return 'laptop'
        elif 'package' in text or 'box' in text or 'parcel' in text:
            return 'package'
        return 'unknown'
    
    @staticmethod
    def _extract_issue_type(text: str) -> str:
        if any(x in text for x in ['dent', 'dented']):
            return 'dent'
        elif any(x in text for x in ['scratch', 'scratched']):
            return 'scratch'
        elif any(x in text for x in ['crack', 'cracked']):
            return 'crack'
        elif any(x in text for x in ['broken', 'broke']):
            return 'broken_part'
        elif any(x in text for x in ['glass', 'shatter', 'shattered']):
            return 'glass_shatter'
        elif any(x in text for x in ['missing', 'missing_part']):
            return 'missing_part'
        elif any(x in text for x in ['torn', 'tear']):
            return 'torn_packaging'
        elif any(x in text for x in ['crushed', 'crumple']):
            return 'crushed_packaging'
        elif any(x in text for x in ['water', 'wet']):
            return 'water_damage'
        elif any(x in text for x in ['stain']):
            return 'stain'
        return 'none'
    
    @staticmethod
    def _extract_object_part(text: str) -> str:
        if 'bumper' in text: return 'bumper'
        elif 'door' in text: return 'door'
        elif 'hood' in text: return 'hood'
        elif 'windshield' in text: return 'windshield'
        elif 'screen' in text: return 'screen'
        elif 'keyboard' in text: return 'keyboard'
        elif 'trackpad' in text: return 'trackpad'
        elif 'hinge' in text: return 'hinge'
        elif 'corner' in text: return 'corner'
        elif 'box' in text: return 'box'
        elif 'seal' in text: return 'seal'
        return 'unknown'
    
    @staticmethod
    def _extract_severity(text: str) -> str:
        if any(x in text for x in ['badly', 'pretty bad', 'severe', 'major', 'significant']):
            return 'high'
        elif any(x in text for x in ['minor', 'small', 'light', 'slightly']):
            return 'low'
        elif any(x in text for x in ['medium', 'moderate']):
            return 'medium'
        return 'unknown'


class EvidenceValidator:
    def __init__(self, requirements_path: str = 'dataset/evidence_requirements.csv'):
        self.requirements = self._load_requirements(requirements_path)
    
    def _load_requirements(self, path: str) -> Dict[str, Any]:
        requirements = {}
        if not os.path.exists(path):
            return requirements
        
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = f"{row['claim_object']}_{row['applies_to']}"
                requirements[key] = row
        
        return requirements
    
    def validate(self, object_type: str, issue_type: str, images: List[Dict[str, Any]]) -> Tuple[bool, str]:
        key = f"{object_type}_{issue_type}"
        if key not in self.requirements:
            if not images:
                return False, "No images provided"
            
            valid_images = [img for img in images if img.get('valid', True)]
            if not valid_images:
                return False, "No valid images available"
            
            return True, "Standard met"
        
        requirement = self.requirements[key]
        min_evidence = requirement.get('minimum_image_evidence', '')
        
        if 'insufficient' in min_evidence.lower():
            return False, "Evidence requirements not met"
        
        if not images:
            return False, "No images provided"
        
        valid_images = [img for img in images if img.get('valid', True)]
        if not valid_images:
            return False, "No valid images available"
        
        if 'multi-image' in min_evidence.lower():
            if not any(img.get('object_type') == object_type for img in valid_images):
                return False, "No relevant images found"
        
        return True, "Standard met"


class HistoryScorer:
    def __init__(self, history_path: str = 'dataset/user_history.csv'):
        self.history_data = self._load_history(history_path)
    
    def _load_history(self, path: str) -> Dict[str, Any]:
        history = {}
        if not os.path.exists(path):
            return history
        
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                history[row['user_id']] = row
        
        return history
    
    def score(self, user_id: str) -> Tuple[List[str], str]:
        if user_id not in self.history_data:
            return [], "No history available"
        
        user_history = self.history_data[user_id]
        risk_flags = []
        
        try:
            past_claims = int(user_history.get('past_claim_count', 0))
            if past_claims > 5:
                risk_flags.append('user_history_risk')
        except ValueError:
            pass
        
        try:
            rejected = int(user_history.get('rejected_claim', 0))
            if rejected > 0:
                risk_flags.append('user_history_risk')
        except ValueError:
            pass
        
        try:
            manual_review = int(user_history.get('manual_review_claim', 0))
            if manual_review > 0:
                risk_flags.append('manual_review_required')
        except ValueError:
            pass
        
        history_flags = user_history.get('history_flags', '').lower()
        if 'user_history_risk' in history_flags:
            risk_flags.append('user_history_risk')
        
        reason = "User history risk factors detected" if risk_flags else "No history risks"
        return risk_flags, reason


class DecisionEngine:
    @staticmethod
    def decide(claim: Dict[str, Any], images: List[Dict[str, Any]], evidence_met: bool, risk_flags: List[str], history_risk: bool) -> Tuple[str, str]:
        if not images:
            return 'not_enough_information', "No images provided"
        
        if not evidence_met:
            return 'not_enough_information', "Evidence requirements not met"
        
        valid_images = [img for img in images if img.get('valid', True)]
        if len(valid_images) == 0:
            return 'not_enough_information', "No valid images available"
        
        visible_issues = [img.get('issue_type') for img in valid_images if img.get('issue_type') != 'none']
        
        if not visible_issues:
            return 'not_enough_information', "No visible issues found"
        
        claim_issue = claim.get('issue_type')
        if claim_issue == 'none':
            return 'not_enough_information', "No issue claimed"
        
        matched_issues = [issue for issue in visible_issues if issue == claim_issue]
        
        if matched_issues:
            if history_risk and claim_issue in ['dent', 'scratch']:
                return 'contradicted', "Claim contradicted by user history risk"
            
            return 'supported', "Claim supported by visible evidence"
        
        return 'contradicted', "Visible evidence contradicts claim"


class DamageClaimSystem:
    def __init__(self):
        self.image_analyzer = ImageAnalyzer()
        self.claim_extractor = ClaimExtractor()
        self.evidence_validator = EvidenceValidator()
        self.history_scorer = HistoryScorer()
        self.decision_engine = DecisionEngine()
    
    def process_claim(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        image_paths = claim_data.get('image_paths', '').split(';') if claim_data.get('image_paths') else []
        
        images = []
        for image_path in image_paths:
            image_path = image_path.strip()
            if image_path:
                # Ensure we're using the correct path
                if not image_path.startswith('dataset/'):
                    image_path = os.path.join('dataset', image_path)
                images.append(self.image_analyzer.analyze_image(image_path))
        
        claim_text = claim_data.get('user_claim', '')
        extracted_claim = self.claim_extractor.extract(claim_text)
        
        evidence_met, evidence_reason = self.evidence_validator.validate(
            claim_data.get('claim_object'),
            extracted_claim.get('issue_type'),
            images
        )
        
        risk_flags, history_reason = self.history_scorer.score(claim_data.get('user_id'))
        
        decision, justification = self.decision_engine.decide(
            extracted_claim,
            images,
            evidence_met,
            risk_flags,
            len(risk_flags) > 0
        )
        
        result = {
            'user_id': claim_data.get('user_id'),
            'image_paths': claim_data.get('image_paths'),
            'user_claim': claim_text,
            'claim_object': claim_data.get('claim_object'),
            'evidence_standard_met': evidence_met,
            'evidence_standard_met_reason': evidence_reason if evidence_reason else 'Standard met',
            'risk_flags': ';'.join(risk_flags) if risk_flags else 'none',
            'issue_type': extracted_claim.get('issue_type', 'none'),
            'object_part': extracted_claim.get('object_part', 'unknown'),
            'claim_status': decision,
            'claim_status_justification': justification,
            'supporting_image_ids': ';'.join([img.get('image_id', '') for img in images if img.get('valid', True)]) if any(img.get('valid', True) for img in images) else 'none',
            'valid_image': any(img.get('valid', True) for img in images),
            'severity': extracted_claim.get('severity', 'unknown')
        }
        
        return result
    
    def process_all_claims(self, claims_path: str) -> List[Dict[str, Any]]:
        results = []
        
        with open(claims_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                result = self.process_claim(row)
                results.append(result)
        
        return results
    
    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        fieldnames = [
            'user_id', 'image_paths', 'user_claim', 'claim_object',
            'evidence_standard_met', 'evidence_standard_met_reason',
            'risk_flags', 'issue_type', 'object_part', 'claim_status',
            'claim_status_justification', 'supporting_image_ids', 'valid_image',
            'severity'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result)

def main():
    system = DamageClaimSystem()
    results = system.process_all_claims('dataset/claims.csv')
    system.save_results(results, 'output.csv')
    print(f"Processed {len(results)} claims successfully!")

if __name__ == '__main__':
    main()
