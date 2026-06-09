from textwrap import dedent
from datetime import datetime
from pathlib import Path
from decouple import config
from agno.agent import Agent
from agno.models.openai import OpenAIResponses
from agno.models.openai.like import OpenAILike
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools
from agno.tools.tavily import TavilyTools

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

instructions=dedent("""\
    IMPORTANT 1: the output of agent should have a VALID MARKDOWN format.
    IMPORTANT 2: check boxes in markdown file should start with "- [ ]" not "[ ]".
    1. Research Phase
   - Extract current version and target version from user's prompt
   - Find official release notes and changelog for the target version
   - Identify breaking changes between current and target version
   - Locate official upgrade documentation from Odoo SA
   - Search for community experiences and known issues for this specific version pair

2. Analysis Phase
   - Compare database schema changes between versions
   - Identify affected custom modules (accounting, inventory, purchase, sales, etc.)
   - Assess Python/Odoo framework API changes
   - Map dependency updates (PostgreSQL, Python packages, Node dependencies)
   - Analyze migration complexity and estimated downtime

3. Technical Planning Phase
   - Create pre-upgrade checklist tailored to the version pair
   - Define backup strategy (database, filestore, custom code)
   - Define rollback strategy with clear steps
   - List required tools (Odoo upgrade scripts, OCA migration tools, database utilities)
   - Determine upgrade order: base modules -> custom -> third-party modules

4. Execution Instructions
   - Provide step-by-step terminal commands (generic, adaptable to Docker/native/Odoo.sh)
   - Include database migration sequence with commands
   - Show custom module adaptation patterns with before/after code examples
   - List post-upgrade validation steps
   - Include environment-specific notes (detect or ask: Docker, Odoo.sh, on-premise)

5. Safety & Verification
   - Validate backups before starting checklist
   - Test in staging environment first (mandatory)
   - Verify data integrity post-migration
   - Provide regression testing checklist
   - Include rollback procedure if issues arise
   - Warn about common pitfalls specific to this version pair
""")

expected_output = dedent("""\
================================================================================
                    ODOO UPGRADE GUIDE
================================================================================
Current Version: {extracted_from_user_prompt}
Target Version:  {extracted_from_user_prompt}
Environment Type: {Docker / Odoo.sh / On-Premise / Unknown - ask user}
Generated: {current_date} at {current_time}
================================================================================

SECTION 1: PRE-UPGRADE ASSESSMENT
================================================================================

1.1 Version Analysis
-------------------
Release Notes Source: [Official Odoo {target_version} changelog]
Breaking Changes Identified: [Yes/No - with summary]
Database Migration Required: [Yes/No]
Estimated Downtime: [minutes/hours]

1.2 Dependency Changes
---------------------
PostgreSQL: [current_version] -> [required_version]
Python: [current_version] -> [required_version]
Node.js: [current_version] -> [required_version]
Key Python Packages: [list changes]

1.3 Custom Modules Impact Assessment
-----------------------------------
Total custom modules: [count]
Modules requiring changes: [count]
Modules with high complexity changes: [count]
Critical modules affected: [list with reasons]

================================================================================
SECTION 2: PRE-UPGRADE CHECKLIST
================================================================================

Complete ALL items before proceeding:

[ ] Backup database - command: [database backup command for their setup]
[ ] Backup filestore - command: [filestore backup command]
[ ] Backup custom addons directory - command: [backup command]
[ ] Tag current code in version control - command: git tag pre-upgrade-{current_version}
[ ] Export current modules list - command: [command]
[ ] Create staging environment clone
[ ] Test backup restore procedure
[ ] Notify users of maintenance window
[ ] Document current performance baseline

================================================================================
SECTION 3: BREAKING CHANGES ANALYSIS
================================================================================

3.1 Database Schema Changes
--------------------------
[List of model changes, field additions/removals, table modifications]

3.2 API Method Changes
---------------------
[List of deprecated/removed methods with replacements]

3.3 View Inheritance Changes
---------------------------
[Changes to XML view architecture]

3.4 JavaScript/OWL Changes
-------------------------
[Frontend framework breaking changes]

3.5 Third-Party Module Compatibility
-----------------------------------
[List of incompatible third-party modules and alternatives]

================================================================================
SECTION 4: UPGRADE EXECUTION PLAN
================================================================================

4.1 Staging Environment Upgrade (MANDATORY FIRST)
-------------------------------------------------
Step 1: Clone production to staging
   Command: [command based on detected environment]

Step 2: Run upgrade in staging
   Command: [command based on environment]

Step 3: Validate staging upgrade
   [Validation checklist]

4.2 Production Upgrade Steps
---------------------------
Step 1: Put system in maintenance mode
   Command: [command]

Step 2: Stop services
   Command: [command]

Step 3: Create final backup
   Command: [command]

Step 4: Update codebase to {target_version}
   Command: [git checkout / docker pull / etc.]

Step 5: Update dependencies
   Command: [pip install / npm install commands]

Step 6: Run database migration
   Command: [odoo-bin or docker exec command with --update=all]

Step 7: Restart services
   Command: [command]

Step 8: Disable maintenance mode
   Command: [command]

================================================================================
SECTION 5: CUSTOM MODULE ADAPTATION PATTERNS
================================================================================

For each affected pattern, use the following conversions:

5.1 Deprecated API Method Pattern
---------------------------------
BEFORE ({current_version}):
   [code example of old pattern]

AFTER ({target_version}):
   [code example of new pattern]

5.2 View Inheritance Pattern
---------------------------
BEFORE ({current_version}):
   [XML example]

AFTER ({target_version}):
   [XML example]

5.3 Field Definition Pattern
---------------------------
[Before/after examples]

5.4 Security Rule Pattern
------------------------
[Before/after examples]

================================================================================
SECTION 6: POST-UPGRADE VALIDATION
================================================================================

Run these tests after upgrade completes:

6.1 System Health Checks
-----------------------
[ ] Check server logs for errors - command: [log command]
[ ] Verify all modules updated - command: [module list command]
[ ] Check database version - command: [SQL query]
[ ] Verify filestore accessibility

6.2 Functional Tests
-------------------
[ ] Login to web interface
[ ] Create and save a sale order
[ ] Create and validate a purchase order
[ ] Create and post an invoice
[ ] Run a report (PDF generation)
[ ] Test each critical custom module

6.3 Performance Tests
--------------------
[ ] Compare dashboard load time: before [X]s vs after [Y]s
[ ] Compare database size: before [X]MB vs after [Y]MB
[ ] Check query execution times

================================================================================
SECTION 7: ROLLBACK PROCEDURE
================================================================================

If upgrade fails or critical issues are found:

7.1 Complete Rollback Steps
--------------------------
Step 1: Stop services
   Command: [command]

Step 2: Restore database from backup
   Command: [database restore command]

Step 3: Restore filestore
   Command: [filestore restore command]

Step 4: Revert code to {current_version}
   Command: [git checkout / docker tag command]

Step 5: Restart services
   Command: [command]

Step 6: Verify rollback success
   [Verification steps]

7.2 Partial Rollback (Module Level)
----------------------------------
[Steps to rollback individual problematic modules]

================================================================================
SECTION 8: TROUBLESHOOTING COMMON ISSUES
================================================================================

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| [Error 1]     | [Cause]      | [Fix]    |
| [Error 2]     | [Cause]      | [Fix]    |
| [Error 3]     | [Cause]      | [Fix]    |

================================================================================
SECTION 9: ENVIRONMENT-SPECIFIC NOTES
================================================================================

9.1 For Docker Environments
--------------------------
- Volume backup commands: [commands]
- Container upgrade sequence: [steps]
- Image tagging strategy: [strategy]

9.2 For Odoo.sh Environments
---------------------------
- Branch strategy: [steps]
- Staging deployment: [steps]
- Production deployment: [steps]

9.3 For On-Premise (Native) Environments
---------------------------------------
- Service management commands: [commands]
- Virtual environment handling: [steps]
- Nginx/Apache considerations: [notes]

================================================================================
SECTION 10: SOURCES & METHODOLOGY
================================================================================

Official Documentation:
- Odoo {target_version} Release Notes: [URL or search terms]
- Odoo Upgrade Documentation: [source]
- Odoo Migration Tools: [source]

Community Resources:
- OCA Migration Tools
- Verified upgrade reports for {current_version} -> {target_version}
- Community forum threads

Methodology:
- Breaking changes identified from official changelog
- Custom module analysis based on API deprecation patterns
- Upgrade path validated through community experience

================================================================================
                            END OF UPGRADE GUIDE
================================================================================

IMPORTANT REMINDERS:
1. Always test in staging FIRST - never upgrade production directly
2. Verify backups are restorable before starting
3. Document any custom modifications made during upgrade
4. Keep maintenance window 2x your estimated time
5. Have rollback plan ready before executing upgrade

Generated by Odoo Upgrade Specialist AI
================================================================================
""")


# Create custom DuckDuckGo tool with retry logic
class ResilientDuckDuckGoTools(DuckDuckGoTools):
    def web_search(self, query: str, max_results: int = 10) -> str:
        """Search web with retry logic"""
        import time
        from ddgs import DDGS

        # Try multiple search variations
        search_queries = [
            query,
            f'"{query}"',  # Exact match
            query.replace("documentation", "guide"),  # Alternative terms
            query.replace("upgrade", "migration"),
        ]

        for attempt in range(3):  # 3 attempts
            for search_query in search_queries[:2]:  # Try first 2 variations
                try:
                    print(f"🔍 Searching: {search_query} (attempt {attempt + 1})")

                    with DDGS() as ddgs:
                        results = list(ddgs.text(search_query, max_results=max_results))

                        if results:
                            formatted = []
                            for r in results[:max_results]:
                                formatted.append(f"- {r['title']}\n  {r['body']}\n  URL: {r['href']}")

                            if formatted:
                                return "\n\n".join(formatted)

                except Exception as e:
                    print(f"⚠️ Search failed for '{search_query}': {e}")
                    time.sleep(2)  # Wait before retry

            time.sleep(3)  # Wait between attempts

        return f"⚠️ Unable to search for: {query}. Please check internet connection or try manual search."

model = OpenAILike(
            id="gpt-4o-mini",
            api_key=config("METIS_API_KEY"),
            base_url=config("METIS_BASE_URL")
        )

# Initialize the research agent with advanced journalistic capabilities
research_agent = Agent(
    model=model,
    # tools=[DuckDuckGoTools(), Newspaper4kTools()],
    tools=[ResilientDuckDuckGoTools(), Newspaper4kTools()],
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