#!/usr/bin/env python3
"""
Normalize OpenStreetMap features to Environment Ontology (EnvO) terms.

This script processes NMDC biosamples that have been enriched with OpenStreetMap 
features and maps these features to standardized EnvO terms. It uses the OAK 
(Ontology Access Kit) to properly interact with the EnvO ontology through native 
methods, not SQL queries. A PydanticAI agent with specialized tools is used to 
make intelligent mapping decisions.
"""

import json
import logging
import os
import re
import click
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from tqdm import tqdm
from time import sleep
from dataclasses import dataclass
import asyncio

# PydanticAI imports
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# OAK imports
from oaklib import get_adapter
from oaklib.datamodels.text_annotator import TextAnnotationConfiguration
from oaklib.utilities.lexical.lexical_indexer import (
    load_lexical_index,
    create_lexical_index,
    save_lexical_index
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(verbose=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MIN_ANNOTATION_LENGTH = 3
LEX_INDEX_FILE = "envo_lexical_index.yaml"
CONFIDENCE_THRESHOLD = 0.7

class OSMFeature(BaseModel):
    """OpenStreetMap feature extracted from the enriched biosample data"""
    feature_id: str = Field(..., description="OSM identifier for the feature")
    feature_type: str = Field(..., description="Type of the feature (e.g., 'natural:water')")
    tags: Dict[str, str] = Field(..., description="OSM tags with environmental relevance")
    coordinates: Tuple[float, float] = Field(..., description="Latitude and longitude")
    distance_from_center: float = Field(..., description="Distance in meters from the sample location")
    area: Optional[float] = Field(None, description="Area of the feature in square meters if available")

class EnvOMapping(BaseModel):
    """Mapping from an OSM feature to an EnvO term"""
    envo_id: str = Field(..., pattern=r"^ENVO:\d{8}$", description="EnvO identifier (format: ENVO:XXXXXXXX)")
    envo_label: str = Field(..., min_length=1, description="Human-readable EnvO term label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(..., min_length=10, description="Explanation for the mapping decision")
    feature_id: str = Field(..., description="ID of the OSM feature being mapped")
    feature_type: str = Field(..., description="Type of the OSM feature being mapped")
    distance: float = Field(..., description="Distance from the sample location in meters")
    nmdc_field: Optional[str] = Field(None, description="Suggested NMDC field this mapping corresponds to (env_broad_scale, env_local_scale, or env_medium)")
    nmdc_field_confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence in the NMDC field assignment")

class EnvOLookupResult(BaseModel):
    """Result of an EnvO term lookup"""
    id: str = Field(..., description="EnvO ID (e.g., 'ENVO:00000097')")
    label: str = Field(..., description="Human-readable label for the EnvO term")
    is_obsolete: bool = Field(False, description="Whether the term is marked as obsolete")
    definition: Optional[str] = Field(None, description="Definition of the term if available")

class TextAnnotationResult(BaseModel):
    """Result of text annotation with EnvO terms"""
    text: str = Field(..., description="Original text that was annotated")
    matches: List[Dict[str, Any]] = Field(..., description="EnvO terms found in the text")
    coverage: float = Field(..., ge=0.0, le=1.0, description="Proportion of text covered by annotations")

class EnvOHelper:
    """Helper class for EnvO ontology operations using OAK"""
    
    def __init__(self):
        """Initialize the EnvO helper with OAK adapter"""
        # Use OAK SQLite implementation for EnvO
        self.adapter = get_adapter("sqlite:obo:envo")
        
        # Configure text annotation
        self.annotation_config = TextAnnotationConfiguration()
        self.annotation_config.match_whole_words_only = True
        
        # Load or create lexical index
        self._load_lexical_index()
    
    def _load_lexical_index(self):
        """Load existing lexical index or create a new one"""
        try:
            self.lexical_index = load_lexical_index(LEX_INDEX_FILE)
            logger.info(f"Loaded existing lexical index from {LEX_INDEX_FILE}")
        except FileNotFoundError:
            logger.info(f"Creating new lexical index for EnvO")
            self.lexical_index = create_lexical_index(self.adapter)
            save_lexical_index(self.lexical_index, LEX_INDEX_FILE)
            logger.info(f"Saved new lexical index to {LEX_INDEX_FILE}")
    
    def get_term_info(self, envo_id: str) -> Optional[EnvOLookupResult]:
        """
        Get information about an EnvO term by ID.
        
        Args:
            envo_id: EnvO identifier (e.g., 'ENVO:00000097')
            
        Returns:
            EnvOLookupResult with term details or None if term not found
        """
        try:
            # Normalize to uppercase prefix
            envo_id = envo_id.replace("envo:", "ENVO:")
            
            # Check if term exists
            if envo_id not in self.adapter.entities():
                return None
            
            # Get label
            labels = list(self.adapter.labels(envo_id))
            if not labels:
                return None
                
            # Check if obsolete
            is_obsolete = self.adapter.is_obsolete(envo_id)
            
            # Get definition if available
            definitions = list(self.adapter.definitions(envo_id))
            definition = definitions[0] if definitions else None
            
            return EnvOLookupResult(
                id=envo_id,
                label=labels[0],
                is_obsolete=is_obsolete,
                definition=definition
            )
            
        except Exception as e:
            logger.warning(f"Error getting info for {envo_id}: {e}")
            return None
    
    def is_true_whole_word_match(self, text: str, match_string: str) -> bool:
        """Verify if match_string occurs as a complete word"""
        words = re.findall(r"\b\w+\b", text.lower())
        return match_string.lower() in words
    
    def filter_annotations(self, annotations, text):
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
                if not self.is_true_whole_word_match(text, match_string):
                    continue
            
            filtered.append(ann)
        return filtered
    
    def compute_annotation_coverage(self, annotations, text_length):
        """Calculate what percentage of text is covered by annotations"""
        if not annotations or text_length == 0:
            return 0
            
        intervals = []
        for ann in annotations:
            if hasattr(ann, "subject_start") and hasattr(ann, "subject_end"):
                intervals.append((ann.subject_start, ann.subject_end))
                
        if not intervals:
            return 0
            
        # Merge overlapping intervals
        intervals.sort(key=lambda x: x[0])
        merged = []
        current_start, current_end = intervals[0]
        
        for start, end in intervals[1:]:
            if start <= current_end + 1:  # Adjacent or overlapping
                current_end = max(current_end, end)
            else:
                merged.append((current_start, current_end))
                current_start, current_end = start, end
                
        merged.append((current_start, current_end))
        
        total_covered = sum(end - start + 1 for start, end in merged)
        return total_covered / text_length
    
    def annotate_text(self, text: str) -> TextAnnotationResult:
        """
        Find EnvO terms in text using OAK annotation.
        
        Args:
            text: Text to annotate with EnvO terms
            
        Returns:
            TextAnnotationResult with matches and coverage metrics
        """
        try:
            # Get text annotations
            annotations = self.adapter.annotate_text(
                text, configuration=self.annotation_config
            )
            
            # Filter and process annotations
            filtered = self.filter_annotations(annotations, text)
            
            # Calculate coverage
            coverage = self.compute_annotation_coverage(filtered, len(text))
            
            # Convert to structured format
            matches = []
            for ann in filtered:
                term_id = ann.object_id
                if term_id.startswith("ENVO:"):
                    label = list(self.adapter.labels(term_id))[0]
                    matches.append({
                        "id": term_id,
                        "label": label,
                        "match": ann.match_string,
                        "start": ann.subject_start,
                        "end": ann.subject_end
                    })
            
            return TextAnnotationResult(
                text=text,
                matches=matches,
                coverage=coverage
            )
            
        except Exception as e:
            logger.error(f"Error annotating text: {e}")
            return TextAnnotationResult(
                text=text,
                matches=[],
                coverage=0.0
            )

class EnvoNormalizerAgent(Agent):
    """PydanticAI agent for mapping OSM features to EnvO terms."""
    
    def __init__(self):
        """Initialize the EnvO normalizer agent with OAK helper and model."""
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
            from OpenStreetMap to standardized Environment Ontology (EnvO) terms for NMDC biosamples.
            
            Your task is to analyze OSM features and determine the most appropriate EnvO term 
            for each feature, considering:
            1. The primary feature type (e.g., 'natural:water', 'landuse:forest')
            2. All relevant OSM tags describing the feature
            3. The distance from the point of interest
            4. Any relevant EnvO terms found in the feature description
            5. The biosample's existing EnvO terms (if provided)
            
            In NMDC biosamples, there are three important environmental fields:
            - env_broad_scale: The broad-scale environment context (e.g., biomes, large environmental systems)
            - env_local_scale: The local environment context (e.g., habitats, ecosystems)
            - env_medium: The environmental material (e.g., soil, water, air, sediment)
            
            When selecting an EnvO term:
            - Prefer terms that match the feature's environmental character
            - Consider how the feature would influence the local environment
            - Only use terms that exist in the EnvO ontology
            - Provide a confidence score based on how well the mapping fits
            - Explain your reasoning clearly
            - Suggest which NMDC field (env_broad_scale, env_local_scale, env_medium) this term would be appropriate for
            
            For features very far from the sample location (>500m), reduce confidence
            unless they are likely to have broad environmental impact.
            """
        )
    
    @Agent.tool
    def get_envo_term(self, ctx: RunContext, envo_id: str) -> EnvOLookupResult:
        """
        Look up information about an EnvO term by ID.
        
        Args:
            envo_id: The EnvO identifier to look up (e.g., 'ENVO:00000097')
            
        Returns:
            Information about the EnvO term including label, obsolete status, and definition
        """
        result = self.envo_helper.get_term_info(envo_id)
        if not result:
            return EnvOLookupResult(
                id=envo_id,
                label="TERM NOT FOUND",
                is_obsolete=False,
                definition=None
            )
        return result
    
    @Agent.tool
    def annotate_text_with_envo(self, ctx: RunContext, text: str) -> TextAnnotationResult:
        """
        Find EnvO terms in text using the EnvO ontology.
        
        Args:
            text: Text to analyze for environmental terms
            
        Returns:
            EnvO terms found in the text with their positions and coverage metrics
        """
        return self.envo_helper.annotate_text(text)
    
    @Agent.tool
    def search_envo_terms(self, ctx: RunContext, query: str, max_results: int = 5) -> List[EnvOLookupResult]:
        """
        Search for EnvO terms matching a query string.
        
        Args:
            query: Search string to find matching EnvO terms
            max_results: Maximum number of results to return (default: 5)
            
        Returns:
            List of matching EnvO terms with their details
        """
        results = []
        try:
            # Use basic search functionality
            search_results = self.envo_helper.adapter.basic_search(query)
            
            # Get full details for each result
            for term_id in list(search_results)[:max_results]:
                term_info = self.envo_helper.get_term_info(term_id)
                if term_info and not term_info.is_obsolete:
                    results.append(term_info)
            
            return results
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []
    
    async def map_feature_to_envo(self, feature: OSMFeature, biosample_env_terms: Optional[Dict[str, Dict[str, str]]] = None) -> Optional[EnvOMapping]:
        """
        Map an OSM feature to the most appropriate EnvO term.
        
        Args:
            feature: OSM feature to map
            biosample_env_terms: Existing environment terms in the biosample (optional)
            
        Returns:
            EnvO mapping with confidence and reasoning
        """
        try:
            # Create feature description
            feature_desc = (
                f"OSM Feature Type: {feature.feature_type}\n"
                f"Distance from sample: {feature.distance_from_center} meters\n"
                f"Tags: {feature.tags}\n"
            )
            
            # Add biosample's asserted environment terms for context
            env_context = ""
            if biosample_env_terms:
                env_context = "\nExisting biosample environment terms:\n"
                for field, term in biosample_env_terms.items():
                    env_context += f"- {field}: {term['id']} ({term['name']})\n"
            
            # Use annotation tool to find relevant terms
            annotation_result = await self.annotate_text_with_envo(feature_desc)
            
            # Add matches to the description
            terms_text = ""
            if annotation_result.matches:
                terms_text = "\nEnvO terms found in description:\n"
                for match in annotation_result.matches:
                    terms_text += f"- {match['id']} ({match['label']}): '{match['match']}'\n"
            
            # For specific feature types, suggest relevant EnvO terms
            suggestions = ""
            if feature.feature_type.startswith("natural:water") or "water" in feature.tags:
                water_terms = await self.search_envo_terms("water body")
                if water_terms:
                    suggestions += "\nSuggested water body terms:\n"
                    for term in water_terms:
                        suggestions += f"- {term.id} ({term.label})\n"
            elif feature.feature_type.startswith("natural:forest") or "forest" in feature.tags:
                forest_terms = await self.search_envo_terms("forest")
                if forest_terms:
                    suggestions += "\nSuggested forest terms:\n"
                    for term in forest_terms:
                        suggestions += f"- {term.id} ({term.label})\n"
            elif feature.feature_type.startswith("landuse:") or "landuse" in feature.tags:
                landuse_terms = await self.search_envo_terms("land use")
                if landuse_terms:
                    suggestions += "\nSuggested land use terms:\n"
                    for term in landuse_terms:
                        suggestions += f"- {term.id} ({term.label})\n"
            
            # Prepare query
            query = f"""Analyze this OpenStreetMap feature and map it to the most appropriate EnvO term:

Feature Description:
{feature_desc}
{env_context}
{terms_text}
{suggestions}

Please determine the most appropriate EnvO term that represents this geographical feature and its environmental significance.
Also determine which NMDC environmental field this term would be most appropriate for.

Respond with a JSON object containing:
1. envo_id: The EnvO ID in the format ENVO:XXXXXXXX
2. envo_label: The human-readable label for the EnvO term
3. confidence: A score between 0.0 and 1.0 indicating your confidence in this mapping
4. reasoning: Your explanation for why this EnvO term is appropriate
5. nmdc_field: The NMDC field this term would be most appropriate for (env_broad_scale, env_local_scale, or env_medium)
6. nmdc_field_confidence: A score between 0.0 and 1.0 indicating your confidence in the field assignment

JSON format:
{{
  "envo_id": "ENVO:XXXXXXXX",
  "envo_label": "term name",
  "confidence": 0.95,
  "reasoning": "explanation",
  "nmdc_field": "env_local_scale",
  "nmdc_field_confidence": 0.85
}}
"""
            
            # Get the agent's response
            result = await self.run(query)
            
            # Extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', result.data, re.DOTALL)
            if not json_match:
                json_match = re.search(r'{.*}', result.data, re.DOTALL)
            
            if not json_match:
                logger.warning(f"Could not extract JSON from response: {result.data[:100]}...")
                return None
                
            json_str = json_match.group(1) if json_match.group(0).startswith('```') else json_match.group(0)
            
            # Parse the mapping
            mapping_data = json.loads(json_str)
            
            # Validate the EnvO ID
            term_info = await self.get_envo_term(mapping_data["envo_id"])
            if term_info.label == "TERM NOT FOUND":
                logger.warning(f"Invalid EnvO ID suggested: {mapping_data['envo_id']}")
                return None
                
            # Create the mapping with feature ID and type
            mapping = EnvOMapping(
                envo_id=mapping_data["envo_id"],
                envo_label=term_info.label,  # Use the validated label
                confidence=mapping_data["confidence"],
                reasoning=mapping_data["reasoning"],
                feature_id=feature.feature_id,
                feature_type=feature.feature_type,
                distance=feature.distance_from_center,
                nmdc_field=mapping_data.get("nmdc_field"),
                nmdc_field_confidence=mapping_data.get("nmdc_field_confidence")
            )
            
            return mapping
            
        except Exception as e:
            logger.error(f"Error mapping feature {feature.feature_id}: {e}")
            return None

# Function is no longer used - we process features directly in process_biosample

def extract_biosample_env_terms(biosample: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Extract asserted environment terms from a biosample.
    
    Args:
        biosample: Dictionary containing biosample metadata
        
    Returns:
        Dictionary with environment terms by field
    """
    env_terms = {}
    
    # Extract environment terms
    for field in ['env_broad_scale', 'env_local_scale', 'env_medium']:
        if field in biosample:
            field_data = biosample[field]
            if isinstance(field_data, dict):
                if 'term' in field_data and isinstance(field_data['term'], dict):
                    env_terms[field] = {
                        'id': field_data['term'].get('id', ''),
                        'name': field_data['term'].get('name', '')
                    }
                elif 'has_raw_value' in field_data:
                    # Handle raw values that might be EnvO IDs
                    raw_val = field_data['has_raw_value']
                    if raw_val.startswith('ENVO_'):
                        # Convert ENVO_XXXXXXXX to ENVO:XXXXXXXX format
                        envo_id = raw_val.replace('ENVO_', 'ENVO:')
                        env_terms[field] = {
                            'id': envo_id,
                            'name': raw_val  # We don't have the name in this case
                        }
                    else:
                        env_terms[field] = {
                            'id': '',
                            'name': raw_val
                        }
    
    return env_terms

def extract_osm_features(biosample: Dict[str, Any]) -> List[OSMFeature]:
    """
    Extract OSM features from a biosample's metadata.
    
    Args:
        biosample: Biosample dictionary with OSM features
        
    Returns:
        List of OSM features as structured objects
    """
    features = []
    
    if 'osm_features' not in biosample:
        return features
        
    # Get asserted environment terms for context
    env_terms = extract_biosample_env_terms(biosample)
    
    # Track categories to avoid duplicate processing
    processed_categories = set()
    
    # Process primary categories first (water, natural, landuse, etc.)
    primary_categories = ['water', 'natural', 'landuse', 'ecosystem', 'protected_area']
    
    # First pass: extract features from primary categories
    for category in primary_categories:
        if category in biosample['osm_features'].get('features', {}):
            processed_categories.add(category)
            
            # For each feature in the category
            for feature_data in biosample['osm_features']['features'][category]:
                try:
                    # Extract coordinates
                    if isinstance(feature_data.get('coordinates'), list) and len(feature_data.get('coordinates')) == 2:
                        coordinates = tuple(feature_data['coordinates'])
                    else:
                        continue
                        
                    # Create feature object
                    feature = OSMFeature(
                        feature_id=feature_data.get('id', f"unknown-{len(features)}"),
                        feature_type=feature_data.get('type', f"{category}:unknown"),
                        tags=feature_data.get('environmental_tags', {}),
                        coordinates=coordinates,
                        distance_from_center=feature_data.get('distance_from_center', 0.0),
                        area=feature_data.get('area')
                    )
                    
                    # Only include features within 500m for better relevance
                    if feature.distance_from_center <= 500:
                        features.append(feature)
                    
                except Exception as e:
                    logger.warning(f"Error processing feature: {e}")
                    continue
    
    # Second pass: extract features from remaining categories
    for category, category_features in biosample['osm_features'].get('features', {}).items():
        if category in processed_categories:
            continue
            
        processed_categories.add(category)
        
        for feature_data in category_features:
            try:
                # Extract coordinates
                if isinstance(feature_data.get('coordinates'), list) and len(feature_data.get('coordinates')) == 2:
                    coordinates = tuple(feature_data['coordinates'])
                else:
                    continue
                    
                # Create feature object
                feature = OSMFeature(
                    feature_id=feature_data.get('id', f"unknown-{len(features)}"),
                    feature_type=feature_data.get('type', f"{category}:unknown"),
                    tags=feature_data.get('environmental_tags', {}),
                    coordinates=coordinates,
                    distance_from_center=feature_data.get('distance_from_center', 0.0),
                    area=feature_data.get('area')
                )
                
                # Only include features within 500m for better relevance
                if feature.distance_from_center <= 500:
                    features.append(feature)
                    
            except Exception as e:
                logger.warning(f"Error processing feature: {e}")
                continue
    
    # Sort by distance
    features.sort(key=lambda f: f.distance_from_center)
    
    # Limit to a reasonable number of features, with bias toward diverse types
    if len(features) > 20:
        # Extract feature types
        feature_types = set(f.feature_type for f in features)
        
        # Keep at least one of each type
        selected_features = []
        for ftype in feature_types:
            type_features = [f for f in features if f.feature_type == ftype]
            # Take the closest one of each type
            if type_features:
                selected_features.append(type_features[0])
        
        # If we still have room, add more features based on distance
        remaining_slots = 20 - len(selected_features)
        if remaining_slots > 0:
            # Get features not already selected
            remaining_features = [f for f in features if f not in selected_features]
            # Sort by distance and take the closest ones
            remaining_features.sort(key=lambda f: f.distance_from_center)
            selected_features.extend(remaining_features[:remaining_slots])
            
        # Sort final selection by distance
        selected_features.sort(key=lambda f: f.distance_from_center)
        return selected_features
    
    return features

async def process_biosample(agent: EnvoNormalizerAgent, biosample: Dict[str, Any], 
                         max_features: int = 20) -> Dict[str, Any]:
    """
    Process a single biosample to add EnvO mappings for its OSM features.
    
    Args:
        agent: EnvO normalizer agent
        biosample: Dictionary containing biosample metadata with OSM features
        max_features: Maximum number of features to process
        
    Returns:
        Biosample dictionary enriched with EnvO mappings
    """
    # Extract biosample's existing EnvO terms for context
    env_terms = extract_biosample_env_terms(biosample)
    
    # Extract OSM features
    features = extract_osm_features(biosample)
    
    if not features:
        logger.warning(f"No OSM features found for biosample {biosample.get('id')}")
        return biosample
    
    # Limit number of features to process
    if len(features) > max_features:
        logger.info(f"Limiting from {len(features)} to {max_features} features for biosample {biosample.get('id')}")
        features = features[:max_features]
    
    # Process features to get EnvO mappings
    mappings_by_type = {}
    
    # Process each feature with the agent
    for feature in features:
        try:
            mapping = await agent.map_feature_to_envo(feature, env_terms)
            if mapping and mapping.confidence >= CONFIDENCE_THRESHOLD:
                if feature.feature_type not in mappings_by_type:
                    mappings_by_type[feature.feature_type] = []
                mappings_by_type[feature.feature_type].append(mapping)
        except Exception as e:
            logger.error(f"Error mapping feature {feature.feature_type}: {e}")
    
    # Group mappings by NMDC field for easier comparison with asserted values
    mappings_by_field = {
        'env_broad_scale': [],
        'env_local_scale': [],
        'env_medium': []
    }
    
    # Sort all mappings by field and confidence
    for feature_type, mappings in mappings_by_type.items():
        for mapping in mappings:
            if mapping.nmdc_field and mapping.nmdc_field in mappings_by_field:
                mappings_by_field[mapping.nmdc_field].append(mapping.dict())
    
    # Sort each field's mappings by confidence (highest first)
    for field in mappings_by_field:
        mappings_by_field[field] = sorted(
            mappings_by_field[field], 
            key=lambda m: m.get('nmdc_field_confidence', 0.0) * m.get('confidence', 0.0),
            reverse=True
        )
    
    # Add EnvO mappings to biosample metadata
    enriched = biosample.copy()
    enriched['envo_mappings'] = {
        feature_type: [mapping.dict() for mapping in mappings]
        for feature_type, mappings in mappings_by_type.items()
    }
    
    enriched['envo_mappings_by_field'] = mappings_by_field
    
    # Add summary statistics
    total_mappings = sum(len(mappings) for mappings in enriched['envo_mappings'].values())
    enriched['envo_mapping_stats'] = {
        'total_features_processed': len(features),
        'features_with_mappings': total_mappings,
        'mapping_coverage': total_mappings / len(features) if features else 0.0,
        'confidence_threshold': CONFIDENCE_THRESHOLD,
        'field_coverage': {
            field: len(mappings) > 0 
            for field, mappings in mappings_by_field.items()
        },
        'agreement_with_asserted': {
            field: any(
                mapping.get('envo_id', '').replace(':', '_') == env_terms.get(field, {}).get('id', '').replace(':', '_')
                for mapping in mappings_by_field[field]
            ) if field in env_terms and mappings_by_field[field] else False
            for field in mappings_by_field
        }
    }
    
    return enriched

@click.command(context_settings=dict(ignore_unknown_options=True))
@click.option('--input', '-i', 'input_path', type=click.Path(exists=True), required=True,
              help='Input JSON file containing NMDC biosamples with OSM features')
@click.option('--output', '-o', 'output_path', type=click.Path(), required=True,
              help='Output path for enriched biosamples JSON with EnvO mappings')
@click.option('--max-samples', type=int, default=None,
              help='Maximum number of samples to process (default: all)')
@click.option('--max-features', type=int, default=20,
              help='Maximum number of features to process per biosample (default: 20)')
@click.option('--confidence', type=float, default=0.7,
              help='Confidence threshold for accepting EnvO mappings (default: 0.7)')
def main_cli(input_path: str, output_path: str, max_samples: int,
          max_features: int, confidence: float):
    """Command-line entry point that runs the async main function."""
    import asyncio
    asyncio.run(main(input_path, output_path, max_samples, max_features, confidence))

async def main(input_path: str, output_path: str, max_samples: int, 
               max_features: int, confidence: float):
    """
    Process NMDC biosamples with OSM features to add EnvO mappings.
    Uses PydanticAI agent with OAK integration to map OSM features to
    standardized EnvO terms.
    """
    global CONFIDENCE_THRESHOLD
    CONFIDENCE_THRESHOLD = confidence
    
    # Load input data
    logger.info(f"Loading biosamples from {input_path}")
    with open(input_path) as f:
        data = json.load(f)
    
    if isinstance(data, dict) and 'biosamples' in data:
        biosamples = data['biosamples']
    else:
        biosamples = data
    
    logger.info(f"Found {len(biosamples)} biosamples with OSM features")
    
    # Limit samples if specified
    if max_samples and max_samples < len(biosamples):
        logger.info(f"Limiting to {max_samples} biosamples")
        biosamples = biosamples[:max_samples]
    
    # Initialize agent
    agent = EnvoNormalizerAgent()
    
    # Process each biosample
    logger.info(f"Processing {len(biosamples)} biosamples")
    enriched_samples = []
    
    for biosample in tqdm(biosamples):
        enriched = await process_biosample(agent, biosample, max_features=max_features)
        enriched_samples.append(enriched)
    
    # Save results
    output_data = {
        'biosamples': enriched_samples,
        'metadata': {
            'total_input_samples': len(biosamples),
            'processed_samples': len(enriched_samples),
            'confidence_threshold': CONFIDENCE_THRESHOLD,
            'max_features_per_sample': max_features
        }
    }
    
    logger.info(f"Writing results to {output_path}")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

if __name__ == "__main__":
    main_cli()