from textwrap import dedent
import json
from datetime import datetime, timedelta
from pathlib import Path
from decouple import config
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.models.openai.like import OpenAILike
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.tools import tool


@tool
def search_odoo_docs(query: str) -> str:
    """Search specifically for Odoo documentation"""
    from ddgs import DDGS

    # Target Odoo's official domains
    specific_query = f"site:odoo.com {query}"

    with DDGS() as ddgs:
        results = list(ddgs.text(specific_query, max_results=5))

    if results:
        formatted = []
        for r in results:
            formatted.append(f"📘 **{r['title']}**\n{r['body']}\n🔗 {r['href']}\n")
        return "\n".join(formatted)
    return ""

description=dedent("""\
You are an elite Odoo technical architect and upgrade specialist with 10+ years of experience. Your expertise encompasses:

- Odoo version upgrade methodologies (major & minor versions)
- Database migration strategies and best practices
- Custom module compatibility assessment and refactoring
- Production environment safety protocols
- Rollback planning and risk mitigation
- Dependency conflict resolution
- Performance optimization post-upgrade
- Testing strategies for upgrade validation
- Odoo.sh vs on-premise upgrade paths
- Common upgrade pitfalls and solutions\
""")

instructions = dedent("""\
    1. Research Phase 🔍
       - Extract current_version and target_version from user prompt
       - Search for: "{target_version} release notes Odoo"
       - Search for: "Odoo {current_version} to {target_version} upgrade guide"
       - Search for: "Odoo {target_version} breaking changes"
       - Search for: "Odoo {target_version} custom module compatibility"
       - Search for: "Odoo {target_version} Docker upgrade"
       - Search for: "Odoo {target_version} upgrade tutorial"
       - Search for: "Odoo {target_version} step by step upgrade"
       - Include video results if they appear in search
       - Extract video URLs for the sources section

    2. Analysis Phase - Use Search Results
       - Extract breaking changes from official release notes
       - Identify database migration requirements
       - Find community reported issues and solutions
       - Document version-specific API changes

    3. Generate Comprehensive Guide
       - Include version numbers in all commands and examples
       - Reference official documentation from search results
       - Add community tips and warnings
       - Provide Docker-specific commands based on search findings
    
    When citing sources from search results:
    
    1. Evaluate Each URL for Authority:
       - OFFICIAL: odoo.com, odoo.com/documentation, github.com/odoo
       - COMMUNITY: reddit.com, odoo.com/forum, stackoverflow.com
       - PARTNER BLOGS: mark as "Partner Blog" not "Official"
       - UNRELATED: Skip entirely if not about upgrades/migration
    
    2. For Official Documentation:
       - URL must contain: odoo.com/documentation, odoo.com/help, or github.com/odoo/odoo/wiki
       - Page title must include: "upgrade", "migration", "release notes", or "changelog"
    
    3. For Upgrade Guides:
       - Content must contain: upgrade steps, migration commands, or version comparison
       - Do NOT use feature announcement blogs as upgrade guides
    
    4. If No Official Source Found:
       - State: "No official upgrade guide found in search results"
       - Use community sources but clearly mark them as "Community Verified"
       - Do not fabricate official URLs
       
    IMPORTANT 1: do not wrap the output inside a "```markdown ```" code format. just leave the markdown alone.
""")

expected_output = dedent("""\
================================================================================
                    ODOO UPGRADE GUIDE
================================================================================
Current Version: {extracted_from_user_prompt}
Target Version:  {extracted_from_user_prompt}
Environment Type: {Docker / Odoo.sh / On-Premise}
Generated: {current_date} at {current_time}
Search Sources Used: {comma_separated_list_of_URLs_from_search_results}
================================================================================

SECTION 1: EXECUTIVE SUMMARY (FROM LATEST SEARCH RESULTS)
================================================================================

Based on official Odoo {target_version} release notes and community reports:

{Summarize key findings from search results - What's new? Is this a major or minor upgrade? Critical warnings?}

**Release Date**: {from_search_results}
**Upgrade Complexity**: {Low/Medium/High - justify from search findings}
**Official Documentation**: {URL_from_search_results}
**Community Sentiment**: {positive/concerned/mixed - from forum searches}

================================================================================
SECTION 2: SEARCH-DRIVEN PRE-UPGRADE ASSESSMENT
================================================================================

2.1 What Search Results Reveal
----------------------------
**Official Release Notes Highlights**:
{Extract 3-5 key bullet points from official changelog search results}

**Community Reported Issues**:
{From forum/reddit/stackoverflow search results - actual problems users faced}

**Known Breaking Changes (Official)**:
{From search results - list specific breaking changes documented by Odoo}

**Migration Time Estimates from Real Users**:
{From community posts - actual downtime experiences}

2.2 Your Environment Assessment
-----------------------------
PostgreSQL Version Required: {from_search_results OR "Unknown - check manually"}
Python Version Required: {from_search_results OR "Unknown - check manually"}
Minimum RAM Recommended: {from_search_results}
Disk Space Needed: {from_search_results}

2.3 Custom Module Impact (Based on Breaking Changes)
---------------------------------------------------
Modules Likely Affected Based on Search Results:
{List module types mentioned in breaking changes - e.g., "Accounting modules changed", "Inventory views updated"}

================================================================================
SECTION 3: SEARCH-VERIFIED UPGRADE CHECKLIST
================================================================================

{For each item, add search findings in brackets}

- [ ] Review official upgrade guide - URL: {from_search_results}
- [ ] Check community upgrade reports - {link_if_found}
- [ ] Backup database - Command: [command]
- [ ] Backup filestore - Command: [command]
- [ ] Test in staging first (MANDATORY per {X} community posts)
- [ ] Verify custom modules against {list_of_affected_apis_from_search}
- [ ] Notify users - Estimated downtime: {from_community_experience}
- [ ] {Any version-specific item found in search results}

================================================================================
SECTION 4: BREAKING CHANGES (FROM OFFICIAL SOURCES)
================================================================================

4.1 Database Changes (Official)
-----------------------------
{From release notes search results - list specific model/field changes}
Source: {URL}

4.2 API Changes (Official + Community)
------------------------------------
{List deprecated/removed methods found in search results}
Community workarounds: {if found}

4.3 View/UI Changes (Official)
----------------------------
{From changelog - XML/JS/OWL changes}
Migration patterns: {from official migration guide search}

4.4 Third-Party Module Compatibility (Community)
----------------------------------------------
{From forum searches - which modules break, which have updates}
Verified working: {list}
Known problematic: {list}
No information found for: {list - verify manually}

================================================================================
SECTION 5: STEP-BY-STEP UPGRADE (COMMUNITY-VERIFIED)
================================================================================

⚠️ IMPORTANT: These steps combine official documentation with community-tested procedures

5.1 Pre-Upgrade Preparation
---------------------------
{Steps with community tips in brackets}

Step 1: {command/action}
   Official says: {from_docs}
   Community tip: {from_forum}

Step 2: {command/action}
   Known issue: {from_search_results}
   Prevention: {community_solution}

5.2 Execution (Tested by Community)
-----------------------------------
{Each step annotated with search findings}

Step 1: Enable maintenance mode
   Command: [command]
   
Step 2: Create final backup
   Command: [command]
   ⚠️ {community_warning_about_backup_issue}

Step 3: Update code to {target_version}
   Command: [command]
   Common error: {from_search} → Fix: {community_fix}

Step 4: Update dependencies
   Command: [command]
   {Version-specific requirement from search results}

Step 5: Run database migration
   Command: [command]
   Expected duration: {from_community_reports}
   Progress indicators: {what_to_watch_for}

Step 6: Post-migration tasks
   {Official post-upgrade steps from documentation}
   {Additional steps recommended by community}

================================================================================
SECTION 6: COMMON PITFALLS & SOLUTIONS (FROM SEARCH RESULTS)
================================================================================

Based on {X} community upgrade reports, these are the most frequent issues:

| Issue | Frequency | Official Fix | Community Workaround | Source |
|-------|-----------|--------------|---------------------|--------|
| {Issue 1} | {X% of reports} | {official_solution} | {community_solution} | {URL} |
| {Issue 2} | {X% of reports} | {official_solution} | {community_solution} | {URL} |
| {Issue 3} | {X% of reports} | {official_solution} | {community_solution} | {URL} |

**Prevention Summary**:
{List key prevention measures from community experience}

================================================================================
SECTION 7: CUSTOM MODULE ADAPTATION (FROM COMMUNITY PATTERNS)
================================================================================

Based on search results, here are adaptation patterns for the affected APIs:

7.1 Pattern: {deprecated_pattern_name_from_search}
---------------------------
Affects modules: {module_types}
Official replacement: {from_docs}
Community adaptation:
   BEFORE ({current_version}):
      {code_example}
   AFTER ({target_version}):
      {code_example}
Source: {URL_of_example}

7.2 Pattern: {another_deprecated_pattern}
---------------------------
[Same structure as above]

7.3 Modules Needing Complete Rewrite
-----------------------------------
{From search results - modules where simple adaptation insufficient}

================================================================================
SECTION 8: POST-UPGRADE VALIDATION (COMMUNITY CHECKLIST)
================================================================================

Community-verified validation tests (from {X} successful upgrades):

Immediate Checks (within 5 minutes):
[ ] Container/Service starts without errors - Command: [command]
[ ] Login works - Known issue: {if_any}
[ ] {Critical_flow_1} works - Test: [steps]
[ ] {Critical_flow_2} works - Test: [steps]

Extended Checks (within 1 hour):
[ ] Scheduled actions run
[ ] Email sending works
[ ] Report generation (PDF)
[ ] {Custom_module_1} functionality
[ ] {Custom_module_2} functionality

Performance Baseline Comparison:
   Before: {metrics_from_community_or_estimate}
   After: {expected_metrics_from_search}
   Warning signs: {what_to_watch_for}

================================================================================
SECTION 9: EMERGENCY PROCEDURES (COMMUNITY-TESTED)
================================================================================

9.1 If Upgrade Fails at Step {common_failure_point_from_search}
--------------------------------------------------------------
Symptoms: {from_search_results}
Likely cause: {from_search}
Immediate action: {community_fix}
Rollback commands:
   Command 1: [command]
   Command 2: [command]
Verification: {how_to_confirm_rollback_succeeded}

9.2 If Database Migration Hangs
-----------------------------
Community solution: {from_forum}
Commands: {specific_commands}
Timeout settings: {recommended_values}

9.3 Contact Resources
-------------------
Official support: {URL_from_search}
Community help: {forum_thread_URLs}
GitHub issues: {relevant_issue_trackers}

================================================================================
SECTION 10: SOURCES & VERIFICATION
================================================================================

This guide was generated using live search results:

Official Sources (accessed {current_date}):
- Release Notes: {URL}
- Upgrade Documentation: {URL}
- Migration Tools: {URL}
- API Changes: {URL}

Community Sources:
- Reddit discussions: {URLs}
- Odoo Forum threads: {URLs}
- Stack Overflow: {URLs}
- GitHub issues: {URLs}
- Medium articles: {URLs}
- YouTube tutorials: {URLs}

Search Statistics:
- Total searches performed: {count}
- Relevant sources found: {count}
- Community reports analyzed: {count}
- Conflicting information identified: {yes/no - if yes, note discrepancies}

================================================================================
SECTION 11: DYNAMIC CONTENT - WHAT'S UNKNOWN
================================================================================

Based on available search results, the following information requires manual verification:

{List items that search didn't clearly answer - prompts user to check manually}
- [ ] {Unknown_item_1} - Check: {suggested_command_or_URL}
- [ ] {Unknown_item_2} - Check: {suggested_command_or_URL}

To get this information:
1. Run: {command}
2. Visit: {URL}
3. Search for: {suggested_query}

================================================================================
SECTION 12: VERSION-SPECIFIC NOTES (FROM SEARCH)
================================================================================

{target_version} vs {current_version} - Key Differences:
{From search results - what's actually different between these versions}

Why Upgrade to {target_version} (from release notes):
{Benefits listed in official documentation}

Risks Specific to This Upgrade (from community):
{Community-reported issues for this specific version pair}

================================================================================
                            END OF UPGRADE GUIDE
================================================================================

⏱️ Guide Generation Metadata:
   - Search results used: ✅
   - Sources cited: {count}
   - Community reports analyzed: {count}
   - Generation timestamp: {current_timestamp}

Generated by Odoo Upgrade Specialist AI using live search data
================================================================================
""")


# Create custom DuckDuckGo tool with retry logic
class ResilientDuckDuckGoTools(DuckDuckGoTools):
    def web_search(self, query: str, max_results: int = 5) -> str:
        """Search web with retry logic - fixed version"""

        # Try multiple search queries
        search_queries = [
            query,
            f'"{query}"',  # Exact match
            query.replace("release notes", "changelog"),
            query.replace("upgrade", "migration"),
            query.replace("documentation", "guide"),
        ]

        for attempt in range(3):  # 3 attempts
            for search_query in search_queries[:3]:  # Try first 3 variations
                try:
                    print(f"🔍 Searching: {search_query} (attempt {attempt + 1})")

                    # Import here to avoid initialization issues
                    from ddgs import DDGS

                    # DDGS doesn't accept headers parameter - remove it
                    with DDGS() as ddgs:
                        results = list(ddgs.text(
                            search_query,
                            max_results=max_results,
                            region='wt-wt',  # Worldwide
                            safesearch='moderate',
                            timelimit='m'  # Past month for recent results
                        ))

                        if results:
                            formatted = []
                            for r in results[:max_results]:
                                formatted.append(
                                    f"### {r.get('title', 'No title')}\n{r.get('body', 'No content')}\nSource: {r.get('href', 'No URL')}\n")

                            print(f"✅ Found {len(results)} results for: {search_query}")
                            return "\n".join(formatted)

                except Exception as e:
                    print(f"⚠️ Search failed for '{search_query}': {str(e)[:100]}")
                    time.sleep(2)  # Wait before retry

            time.sleep(3)  # Wait between attempts

        # Return empty string to let agent use knowledge
        return ""

class DebugResilientDuckDuckGoTools(ResilientDuckDuckGoTools):
    def web_search(self, query: str, max_results: int = 10) -> str:
        print(f"\n🔍 WEB SEARCH CALLED for: {query}")

        result = super().web_search(query, max_results)

        if "⚠️" in result or "No results" in result:
            print(f"❌ SEARCH FAILED: Returning error message")
            print(f"   Result preview: {result[:100]}...")
        else:
            print(f"✅ SEARCH SUCCESS: Found results")
            print(f"   Result preview: {result[:200]}...")

        return result


class CachedSearchTool(ResilientDuckDuckGoTools):
    def __init__(self, cache_dir="search_cache"):
        super().__init__()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def web_search(self, query: str, max_results: int = 10) -> str:
        # Check cache
        cache_file = self.cache_dir / f"{hash(query)}.json"

        if cache_file.exists():
            modified_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - modified_time < timedelta(hours=24):
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                    print(f"📦 Using cached results for: {query}")
                    return cached['result']

        # Perform search
        result = super().web_search(query, max_results)

        # Save to cache
        with open(cache_file, 'w') as f:
            json.dump({'query': query, 'result': result, 'timestamp': datetime.now().isoformat()}, f)

        return result

model = OpenAILike(
            id="gpt-4o-mini",
            api_key=config("METIS_API_KEY"),
            base_url=config("METIS_BASE_URL")
        )

# Initialize the research agent with advanced journalistic capabilities
research_agent = Agent(
    model=model,
    # tools=[DuckDuckGoTools(), Newspaper4kTools()],
    tools=[CachedSearchTool(), search_odoo_docs, Newspaper4kTools()],
    description=description,
    instructions= instructions,
    expected_output=expected_output,
    markdown=True,
    add_datetime_to_context=True,

)

# Example usage with detailed research request
if __name__ == "__main__":
    response = research_agent.run(
        """Analyze and generate a complete upgrade guide from Odoo 19.0 to Odoo 19.2. 
        My environment is self-hosted using Docker with images from GitHub Container Registry (GHCR). 
        I have 3 custom modules and 100 database records. Include all pre-upgrade checks, 
        breaking changes, step-by-step upgrade commands for Docker, post-upgrade validation, rollback procedures, 
        and common troubleshooting.
        """,
        stream=False,
    )
    markdown_content = response.content

    output_dir = Path("./outputs")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"odoo_upgrade_guide_{timestamp}.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"✅ Markdown saved to: {output_file}")

    print(markdown_content)