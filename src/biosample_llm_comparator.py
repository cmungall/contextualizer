import os
import json
import time
import logging
import click
import sys
import requests
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables including API keys
load_dotenv(verbose=True)
CBORG_API_KEY = os.getenv("CBORG_API_KEY")

logger.info(f"CBORG API key found: {'Yes' if CBORG_API_KEY else 'No'}")

def normalize_term(term: Optional[str]) -> str:
    """Normalize a term for comparison by cleaning and lowercasing."""
    if not term:
        return ""
    return str(term).lower().strip()

def extract_asserted_value(field_value: Any) -> Optional[str]:
    """Extract asserted value from various possible field formats."""
    if not field_value:
        return None
        
    if isinstance(field_value, dict):
        # Try different possible locations of the actual value
        if "has_raw_value" in field_value:
            return field_value["has_raw_value"]
        elif "term" in field_value and isinstance(field_value["term"], dict):
            return field_value["term"].get("name", "")
        elif "value" in field_value:
            return field_value["value"]
    elif isinstance(field_value, str):
        return field_value
        
    return str(field_value)

def compare_with_llm(
    sample_id: str,
    environmental_field: str, 
    asserted_value: Optional[str], 
    inferred_value: Optional[str],
    inferred_confidence: Optional[str] = None,
    sample_location: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use Claude Sonnet to compare asserted and inferred environmental values.
    
    Args:
        sample_id: Biosample ID
        environmental_field: Name of the environmental field being compared
        asserted_value: The original value from the biosample
        inferred_value: The inferred value from map interpretation
        inferred_confidence: Confidence level of the inference
        sample_location: Location information for context
        
    Returns:
        Dictionary with LLM analysis
    """
    if not CBORG_API_KEY:
        logger.error("CBORG_API_KEY not set, cannot use Claude Sonnet")
        return {
            "error": "CBORG_API_KEY not set",
            "comparison_result": "unknown"
        }
        
    if not asserted_value and not inferred_value:
        return {
            "comparison_result": "both_missing",
            "analysis": "Both asserted and inferred values are missing."
        }
        
    if not asserted_value:
        return {
            "comparison_result": "asserted_missing",
            "analysis": f"Only inferred value available: {inferred_value}"
        }
        
    if not inferred_value:
        return {
            "comparison_result": "inferred_missing",
            "analysis": f"Only asserted value available: {asserted_value}"
        }
    
    # Prepare prompt for Claude
    prompt = f"""
    I need you to analyze the semantic similarity between two environmental descriptors for a biosample.

    Biosample ID: {sample_id}
    Environmental Field: {environmental_field}
    Location: {sample_location or 'Unknown'}
    
    Asserted Value: "{asserted_value}"
    Inferred Value (from map images): "{inferred_value}" 
    Inference Confidence: {inferred_confidence or 'Unknown'}
    
    Please analyze:
    1. How semantically similar these values are (exact match, close match, partial match, or different)
    2. If different, what specific aspects differ
    3. Whether either value appears incorrect based on standard environmental terminology
    4. Which value is likely more precise or standardized
    5. A confidence score for your comparison (0-100%)
    
    Return your analysis in this JSON format:
    {{
      "comparison_result": "exact_match" | "close_match" | "partial_match" | "different",
      "semantic_similarity": 0-100,
      "key_differences": [list specific differences if any],
      "terminology_assessment": {{"asserted": "standard"|"non-standard", "inferred": "standard"|"non-standard"}},
      "recommendation": "use_asserted" | "use_inferred" | "either_valid" | "neither_valid",
      "analysis_confidence": 0-100,
      "reasoning": "Brief explanation of your analysis"
    }}

    Your response should be ONLY the JSON with no additional text.
    """

    # Prepare API request
    api_url = "https://api.cborg.lbl.gov/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CBORG_API_KEY}"
    }
    
    payload = {
        "model": "anthropic/claude-sonnet",
        "messages": [
            {"role": "system", "content": "You are an expert in environmental science and biology, specializing in comparing and analyzing environmental classifications."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,  # Low temperature for more deterministic responses
        "max_tokens": 1000
    }
    
    try:
        # Call Claude Sonnet through CBORG API
        logger.info(f"Calling Claude Sonnet to compare values for {sample_id} - {environmental_field}")
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract the content from Claude's response
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            
            # Parse JSON response
            try:
                analysis = json.loads(content)
                logger.info(f"Successfully compared values for {sample_id} - {environmental_field}: {analysis['comparison_result']}")
                return analysis
            except json.JSONDecodeError:
                logger.error(f"Failed to parse Claude's response as JSON: {content}")
                return {
                    "error": "Failed to parse LLM response",
                    "comparison_result": "parsing_error",
                    "raw_response": content
                }
        else:
            logger.error(f"Unexpected response format from Claude: {result}")
            return {
                "error": "Unexpected response format",
                "comparison_result": "api_error"
            }
            
    except Exception as e:
        logger.error(f"Error calling Claude Sonnet API: {e}")
        return {
            "error": str(e),
            "comparison_result": "api_error"
        }

def process_sample(sample: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single biosample to compare asserted and inferred environmental values.
    
    Args:
        sample: A biosample with map_interpretations
        
    Returns:
        Enhanced biosample with LLM comparisons
    """
    sample_id = sample.get('id', 'unknown')
    logger.info(f"Processing comparisons for sample {sample_id}")
    
    # Skip if no map interpretations
    if 'map_interpretations' not in sample or 'merged_environmental_factors' not in sample['map_interpretations']:
        logger.warning(f"Sample {sample_id} has no map interpretations to compare")
        return sample
    
    # Get location for context
    location = None
    if 'geo_loc_name' in sample:
        location = extract_asserted_value(sample['geo_loc_name'])
    
    # Fields to compare
    env_fields = [
        "env_broad_scale",
        "env_local_scale", 
        "env_medium",
        "building_setting",
        "cur_land_use",
        "habitat"
    ]
    
    # Initialize comparisons container
    if 'llm_comparisons' not in sample:
        sample['llm_comparisons'] = {}
    
    # Process each field
    for field in env_fields:
        # Extract asserted value
        asserted_value = None
        if field in sample:
            asserted_value = extract_asserted_value(sample[field])
        
        # Extract inferred value
        inferred_value = None
        inferred_confidence = None
        if field in sample['map_interpretations']['merged_environmental_factors']:
            factor = sample['map_interpretations']['merged_environmental_factors'][field]
            inferred_value = factor.get('term')
            inferred_confidence = factor.get('confidence')
        
        # Skip if both values are missing
        if not asserted_value and not inferred_value:
            continue
        
        # Compare using LLM
        comparison = compare_with_llm(
            sample_id=sample_id,
            environmental_field=field,
            asserted_value=asserted_value,
            inferred_value=inferred_value,
            inferred_confidence=inferred_confidence,
            sample_location=location
        )
        
        # Store the comparison
        sample['llm_comparisons'][field] = comparison
        
        # Add short delay to avoid rate limits
        time.sleep(0.5)
    
    return sample

def summarize_comparisons(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of all LLM comparisons across samples.
    
    Args:
        samples: List of biosamples with LLM comparisons
        
    Returns:
        Summary statistics
    """
    summary = {
        "total_samples": len(samples),
        "samples_with_comparisons": 0,
        "total_comparisons": 0,
        "comparison_results": {
            "exact_match": 0,
            "close_match": 0,
            "partial_match": 0,
            "different": 0,
            "asserted_missing": 0,
            "inferred_missing": 0,
            "both_missing": 0,
            "api_error": 0,
            "parsing_error": 0,
            "unknown": 0
        },
        "recommendations": {
            "use_asserted": 0,
            "use_inferred": 0,
            "either_valid": 0,
            "neither_valid": 0
        },
        "field_stats": {
            "env_broad_scale": {"compared": 0, "exact_match": 0, "close_match": 0, "partial_match": 0, "different": 0},
            "env_local_scale": {"compared": 0, "exact_match": 0, "close_match": 0, "partial_match": 0, "different": 0},
            "env_medium": {"compared": 0, "exact_match": 0, "close_match": 0, "partial_match": 0, "different": 0},
            "building_setting": {"compared": 0, "exact_match": 0, "close_match": 0, "partial_match": 0, "different": 0},
            "cur_land_use": {"compared": 0, "exact_match": 0, "close_match": 0, "partial_match": 0, "different": 0},
            "habitat": {"compared": 0, "exact_match": 0, "close_match": 0, "partial_match": 0, "different": 0}
        },
        "average_semantic_similarity": 0,
        "total_semantic_similarity_values": 0
    }
    
    semantic_similarity_sum = 0
    
    # Process each sample
    for sample in samples:
        if 'llm_comparisons' in sample and sample['llm_comparisons']:
            summary["samples_with_comparisons"] += 1
            
            # Process each field comparison
            for field, comparison in sample['llm_comparisons'].items():
                summary["total_comparisons"] += 1
                
                # Count result type
                result = comparison.get("comparison_result", "unknown")
                if result in summary["comparison_results"]:
                    summary["comparison_results"][result] += 1
                else:
                    summary["comparison_results"]["unknown"] += 1
                
                # Count recommendations
                recommendation = comparison.get("recommendation")
                if recommendation in summary["recommendations"]:
                    summary["recommendations"][recommendation] += 1
                
                # Field-specific stats
                if field in summary["field_stats"]:
                    summary["field_stats"][field]["compared"] += 1
                    if result in summary["field_stats"][field]:
                        summary["field_stats"][field][result] += 1
                
                # Collect semantic similarity
                if "semantic_similarity" in comparison:
                    try:
                        similarity = float(comparison["semantic_similarity"])
                        semantic_similarity_sum += similarity
                        summary["total_semantic_similarity_values"] += 1
                    except (ValueError, TypeError):
                        pass
    
    # Calculate average semantic similarity
    if summary["total_semantic_similarity_values"] > 0:
        summary["average_semantic_similarity"] = semantic_similarity_sum / summary["total_semantic_similarity_values"]
    
    return summary

@click.command()
@click.option("--input", 
              default="local/nmdc-ai-map-enriched.json", 
              help="Input JSON file containing biosamples with map_interpretations")
@click.option("--output", 
              default="local/nmdc-llm-comparison.json", 
              help="Output file for enriched biosamples with LLM comparisons")
@click.option("--summary-output", 
              default="local/nmdc-comparison-summary.json", 
              help="Output file for comparison summary statistics")
@click.option("--max-samples", 
              type=int, 
              default=None, 
              help="Maximum number of samples to process (for testing)")
def main(input, output, summary_output, max_samples):
    """Compare asserted and inferred environmental values using Claude Sonnet."""
    logger.info(f"Starting LLM comparison of biosamples from {input}")
    
    # Check for API key
    if not CBORG_API_KEY:
        logger.error("CBORG_API_KEY environment variable not set. Cannot proceed.")
        sys.exit(1)
    
    # Load input file
    try:
        with open(input, 'r') as f:
            samples = json.load(f)
        logger.info(f"Loaded {len(samples)} samples from {input}")
    except Exception as e:
        logger.error(f"Error loading input file: {e}")
        sys.exit(1)
    
    # Limit samples if needed
    if max_samples and max_samples < len(samples):
        logger.info(f"Limiting to {max_samples} samples for processing")
        samples = samples[:max_samples]
    
    # Filter to only samples with map interpretations
    samples_with_interpretations = [s for s in samples if 'map_interpretations' in s]
    logger.info(f"Found {len(samples_with_interpretations)} samples with map interpretations to process")
    
    # Process samples
    processed_samples = []
    for i, sample in enumerate(samples):
        if 'map_interpretations' in sample:
            logger.info(f"Processing sample {i+1}/{len(samples)}: {sample.get('id', 'unknown')}")
            processed_sample = process_sample(sample)
            processed_samples.append(processed_sample)
        else:
            processed_samples.append(sample)
    
    # Generate summary
    summary = summarize_comparisons(processed_samples)
    
    # Write outputs
    with open(output, 'w') as f:
        json.dump(processed_samples, f, indent=2)
    logger.info(f"Wrote {len(processed_samples)} samples to {output}")
    
    with open(summary_output, 'w') as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Wrote comparison summary to {summary_output}")
    
    # Print key stats
    logger.info(f"Comparison Results Summary:")
    logger.info(f"  Total samples with comparisons: {summary['samples_with_comparisons']}")
    logger.info(f"  Total comparisons made: {summary['total_comparisons']}")
    
    if summary['total_comparisons'] > 0:
        exact = summary['comparison_results']['exact_match']
        close = summary['comparison_results']['close_match']
        partial = summary['comparison_results']['partial_match']
        different = summary['comparison_results']['different']
        
        matches = exact + close + partial
        match_pct = matches / summary['total_comparisons'] * 100
        
        logger.info(f"  Match rate (exact+close+partial): {match_pct:.1f}%")
        logger.info(f"  Average semantic similarity: {summary['average_semantic_similarity']:.1f}%")
    
if __name__ == "__main__":
    main()