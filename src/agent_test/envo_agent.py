"""
Agent for mapping OpenStreetMap features to Environment Ontology (EnvO) terms.

This agent uses the Ontology Access Kit (OAK) to properly handle EnvO terms,
following best practices for term lookup, validation, and text annotation.
"""

import os
import re
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from dotenv import load_dotenv

from oaklib import get_adapter
from oaklib.datamodels.text_annotator import TextAnnotationConfiguration

# Load environment variables and configure logging
load_dotenv(verbose=True)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MIN_ANNOTATION_LENGTH = 3

class OSMFeature(BaseModel):
    """OpenStreetMap feature with relevant tags"""
    feature_type: str = Field(..., description="Type of the feature (e.g., 'natural:water')")
    tags: Dict[str, str] = Field(..., description="OpenStreetMap tags associated with the feature")
    distance_from_center: Optional[float] = Field(None, description="Distance in meters from the point of interest")

class EnvOMapping(BaseModel):
    """Mapping of an OSM feature to EnvO terms with confidence"""
    envo_id: str = Field(..., pattern=r"^ENVO:\d{8}$", description="EnvO identifier (format: ENVO:XXXXXXXX)")
    envo_label: str = Field(..., min_length=1, description="Human-readable EnvO term label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(..., min_length=10, description="Explanation for the mapping decision")

class EnvOHelper:
    """Helper class for EnvO ontology operations using OAK"""
    
    def __init__(self):
        """Initialize the EnvO helper with OAK adapter"""
        # Use SQLite implementation for EnvO - OAK handles caching
        self.adapter = get_adapter("sqlite:obo:envo")
        
        # Configure text annotation
        self.annotation_config = TextAnnotationConfiguration()
        self.annotation_config.match_whole_words_only = True
    
    def validate_envo_id(self, envo_id: str) -> bool:
        """Validate if an EnvO ID exists and is not obsolete"""
        try:
            # Normalize to uppercase prefix
            envo_id = envo_id.replace("envo:", "ENVO:")
            return (
                envo_id in self.adapter.entities() and
                not self.adapter.is_obsolete(envo_id)
            )
        except Exception as e:
            logger.warning(f"Error validating {envo_id}: {e}")
            return False
    
    def get_label(self, envo_id: str) -> Optional[str]:
        """Get the label for an EnvO ID"""
        try:
            envo_id = envo_id.replace("envo:", "ENVO:")
            labels = list(self.adapter.labels(envo_id))
            return labels[0] if labels else None
        except Exception as e:
            logger.warning(f"Error getting label for {envo_id}: {e}")
            return None
    
    def is_true_whole_word_match(self, text: str, match_string: str) -> bool:
        """Verify if match_string occurs as a complete word"""
        words = re.findall(r"\b\w+\b", text.lower())
        return match_string.lower() in words
    
    def filter_annotations(self, annotations):
        """Filter annotations based on quality criteria"""
        filtered = []
        for ann in annotations:
            # Skip too-short annotations
            if hasattr(ann, "subject_start") and hasattr(ann, "subject_end"):
                ann_length = ann.subject_end - ann.subject_start + 1
                if ann_length < MIN_ANNOTATION_LENGTH:
                    continue
            
            # Ensure whole word matches for single words
            match_string = getattr(ann, "match_string", None)
            if match_string and " " not in match_string:
                if not self.is_true_whole_word_match(
                    getattr(ann, "subject_text", ""), match_string
                ):
                    continue
            
            filtered.append(ann)
        return filtered
    
    def find_relevant_terms(self, text: str) -> List[Dict[str, str]]:
        """Find relevant EnvO terms in text using OAK annotation"""
        try:
            # Get text annotations
            annotations = self.adapter.annotate_text(
                text, configuration=self.annotation_config
            )
            
            # Filter and process annotations
            filtered = self.filter_annotations(annotations)
            
            # Convert to list of term info
            terms = []
            for ann in filtered:
                term_id = ann.object_id
                if term_id.startswith("ENVO:"):
                    label = self.get_label(term_id)
                    if label:
                        terms.append({
                            "id": term_id,
                            "label": label,
                            "match": ann.match_string
                        })
            
            return terms
            
        except Exception as e:
            logger.error(f"Error finding terms in text: {e}")
            return []

class EnvOMappingAgent(Agent):
    """Agent specialized in mapping OSM features to EnvO terms."""
    
    def __init__(self):
        self.envo_helper = EnvOHelper()
        super().__init__(
            OpenAIModel(
                "anthropic/claude-sonnet",
                provider=OpenAIProvider(
                    base_url="https://api.cborg.lbl.gov",
                    api_key=os.getenv("CBORG_API_KEY"),
                )
            ),
            system_prompt="""You are an expert in environmental ontology helping to map geographical features 
            to standardized Environment Ontology (EnvO) terms. For each OpenStreetMap feature, determine the 
            most appropriate EnvO term, considering:
            
            1. The primary feature type and all relevant OSM tags
            2. The spatial context and distance from the point of interest
            3. Only suggest EnvO terms that have been validated against the ontology
            4. Use the suggested relevant terms as a starting point
            
            Only respond with a valid JSON object in this exact format:
            {
                "envo_id": "ENVO:XXXXXXXX",
                "envo_label": "term name",
                "confidence": 0.95,
                "reasoning": "explanation"
            }
            
            Do not include any other text in your response, just the JSON object.
            Always verify terms exist in EnvO before suggesting them.
            The confidence score should be between 0.0 and 1.0.
            The reasoning should explain why this term is appropriate."""
        )
    
    def process_feature(self, feature: OSMFeature) -> Optional[EnvOMapping]:
        """
        Process a single OSM feature to get EnvO mapping.
        
        Uses OAK to:
        1. Find relevant terms in feature description
        2. Validate suggested EnvO IDs
        3. Look up official labels
        """
        # Create feature description for term search
        feature_text = (
            f"{feature.feature_type} feature with tags: {feature.tags}. "
            f"Distance: {feature.distance_from_center}m"
        )
        
        # Get relevant terms
        relevant_terms = self.envo_helper.find_relevant_terms(feature_text)
        
        # If we found terms, include them in the prompt
        terms_text = ""
        if relevant_terms:
            terms_text = "\n\nRelevant EnvO terms found:\n"
            for term in relevant_terms:
                terms_text += (
                    f"- {term['id']} ({term['label']}) "
                    f"matched: '{term['match']}'\n"
                )
        
        # Create the query
        query = f"""Analyze this OpenStreetMap feature and map it to an EnvO term:
        
        Feature Type: {feature.feature_type}
        Tags: {feature.tags}
        Distance from center: {feature.distance_from_center} meters
        {terms_text}
        Please map this to the most appropriate EnvO term, providing your response in JSON format.
        Only suggest EnvO terms that can be validated against the ontology."""
        
        try:
            # Get the agent's response
            result = self.run_sync(query)
            
            # Clean up the response and parse JSON
            json_str = result.data.strip('`json\n ')
            mapping = EnvOMapping.model_validate_json(json_str)
            
            # Validate the EnvO ID
            if not self.envo_helper.validate_envo_id(mapping.envo_id):
                logger.warning(f"Invalid EnvO ID suggested: {mapping.envo_id}")
                return None
            
            # Verify/update the label
            official_label = self.envo_helper.get_label(mapping.envo_id)
            if official_label and official_label != mapping.envo_label:
                mapping.envo_label = official_label
            
            return mapping
            
        except Exception as e:
            logger.error(f"Error mapping feature: {e}")
            return None

def process_features(features: List[OSMFeature]) -> Dict[str, List[EnvOMapping]]:
    """
    Process a list of OSM features to get EnvO mappings.
    
    Args:
        features: List of OSM features to process
        
    Returns:
        Dictionary mapping feature types to their EnvO mappings
    """
    agent = EnvOMappingAgent()
    mappings = {}
    
    for feature in features:
        try:
            mapping = agent.process_feature(feature)
            if mapping:
                if feature.feature_type not in mappings:
                    mappings[feature.feature_type] = []
                mappings[feature.feature_type].append(mapping)
                
        except Exception as e:
            logger.error(f"Error processing feature {feature.feature_type}: {e}")
            continue
    
    return mappings

if __name__ == "__main__":
    # Test example
    test_feature = OSMFeature(
        feature_type="natural:water",
        tags={
            "natural": "water",
            "water": "lake",
            "name": "Sample Lake"
        },
        distance_from_center=150.0
    )
    
    try:
        print("\nProcessing test feature...")
        mappings = process_features([test_feature])
        
        print("\nTest mapping result:")
        for feature_type, feature_mappings in mappings.items():
            print(f"\nFeature type: {feature_type}")
            for mapping in feature_mappings:
                print(f"EnvO ID: {mapping.envo_id}")
                print(f"EnvO Label: {mapping.envo_label}")
                print(f"Confidence: {mapping.confidence}")
                print(f"Reasoning: {mapping.reasoning}")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise