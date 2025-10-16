# LanceDB Client Discovery - Documentation Pain Points

**Meeting Date**: October 14, 2025
**Participants**: Ayush Chaurasia (LanceDB), Richard Blythman (Naptha)
**Purpose**: Understand LanceDB's documentation quality pain points for pilot program

---

## Executive Summary

LanceDB views documentation as **the #1 product of a dev tool** and a critical part of continuous user onboarding. Their primary pain point is **lack of granular signals** about where users fail in documentation, not necessarily catastrophically broken docs. They want automated testing that provides line-level failure signals and continuous monitoring to keep docs accurate as code evolves.

---

## LanceDB's Documentation Philosophy

### Core Beliefs

**Documentation = Continuous Onboarding**
- Not just reference material - it's the first touchpoint for potential users
- Onboarding isn't just "first run" - users need to become "educated users" who deeply understand the product
- Engineers should "smile after going through a docs page"

**Quote from Ayush**:
> "I mean it's such a nerdy thing to say that an engineer should smile after going through a docs page but I have been there right I know a lot of good docs people who've written good docs page"

### Documentation as a Product

- Hiring senior engineers dedicated to docs (not just writing, but "look and feel, experience")
- Building internal RAG-based bots to catch issues
- Massive opportunity cost if docs are poor - users drop off permanently

---

## Primary Pain Points (Priority Order)

### 1. ⭐⭐⭐ LACK OF GRANULAR FAILURE SIGNALS (Highest Priority)

**The Problem**:
- Google Analytics shows which **pages** are visited
- Cannot track which specific **line or step** causes users to fail
- Users drop off silently - no way to know where they got stuck

**What They Want**:
- Granular signals: "This particular section of this particular subsection is where users keep dropping off"
- Exact step identification in tutorials
- Understanding whether failures are from outdated code, wrong instructions, or unclear explanations

**Quote**:
> "we cannot track user left where user left. They were trying to do something and they could not do it and then they left and then they sort of probably dropped off forever"

**Current Analytics Limitations**:
- Page-level visit tracking (Google Analytics)
- No session tracking (no PostHog or similar yet)
- No conversion tracking from docs → paid users
- No ability to track "which line" caused issues

---

### 2. ⭐⭐ TYPES OF DOCUMENTATION ISSUES

#### A. Outdated Documentation
- Code examples that no longer work with current version
- API signatures that have changed
- Features "implemented merged in code but never came to tutorial section"

#### B. Plain Wrong Information
- Incorrect instructions
- Missing steps in tutorials
- Complexity from multiple offerings creates confusion:
  - Products: Open source, Cloud, Enterprise
  - SDKs: Python, JavaScript, Rust
  - Related tools: LanceDB, Lance file format, Pylance

#### C. Difficult to Follow
- Instructions not informative enough
- Missing context or prerequisites
- Unclear explanations
- "Fuzzy stuff" that's hard to validate automatically

#### D. Missing Coverage
- Features exist in codebase but have NO documentation
- Discord users asking "is this even possible?" when feature exists
- GitHub issues revealing documentation gaps

**Quote**:
> "inaccuracy can be out of date just plain wrong or difficult to follow right or missing steps all of those things"

---

### 3. ⭐ KEEPING DOCS ACCURATE OVER TIME (Continuous Validation)

**Context**: Richard found that LanceDB's current docs are actually mostly accurate
- Code examples work
- API signatures match
- Recent documentation revamp (v2) cleaned up many issues

**Ayush's Response**:
> "we just had a revamp. so a lot of it might be up to date. but yeah the idea would be that we want to make sure it stays up to date. So kind of a cyclist."

**Implication**: Pain point is NOT "everything is broken" - it's **"how do we maintain accuracy as code evolves continuously"**

---

## How They Currently Discover Issues

### Current Failure Signals

**Discord Questions** (Most Common):
- "How to do this with lance - is it even possible?"
- "This is broken"
- "I couldn't do this"
- Feature requests that are actually already implemented but undocumented

**GitHub Issues**:
- Bug reports about missing use cases
- Questions about storage management, features, configurations
- Users raising issues that reveal doc gaps

**Internal Bot Detection**:
- RAG-based bot that embeds samples from LanceDB codebase
- Knows which questions relate to which code snippets
- Can trace back to docstrings
- Bot automatically raises PRs for improvements (example shown in meeting)

### Current Success Signals (Weak)

**Absence of Complaints**:
- Assumed good experience if no one complains
- Not a good metric but it's what they have

**Occasional Positive Feedback**:
- Discord users: "greatest product of all time"
- "really good experience and I enjoyed working with it"
- These are rare but meaningful

**Analytics Growth**:
- Page visits increasing month-over-month
- Shows growing popularity but not doc quality

---

## What They Want from Automated Testing

### Preferred Approach: Fully Automated Agent Testing

**Why This Over Live User Testing**:
- Lower barrier to entry
- Easier to start with
- Can be evaluated by team without needing real users
- Can run continuously as a "cyclist" check

**How They'd Use It**:
1. Agent reads docs like a human developer
2. Agent attempts to implement projects following guides
3. Agent reports specific failures at specific steps
4. **Humans review agent suggestions** to validate they make sense

**Quote**:
> "even before that we'll get some signals because let's say the agent tries something and it will automatically end up recommending some changes right we can just look at those changes if they make sense right because it's super easy to see that okay yes this was missing and we should have done it this way"

### Agent Evaluation Criteria

At each step, the agent should answer:
- Were the instructions clear?
- Was the code example up to date?
- Were there missing prerequisites or steps?
- Did the example execute successfully?

**Granular Reporting Required**:
- Not just "Example #3 failed"
- But "Failed at line 45 of the Quickstart guide in the 'Creating a Table' section"
- Include context: section heading, subsection, step number

---

## Success Metrics & KPIs

### North Star Metric (Aspirational, Untrackable)
> "user comes in and they understand what they read and they can run it on their own right"

Cannot track this once users leave the page (unless using invasive telemetry)

### Practical Metrics They Want

**1. Reduction in Support Requests**
- Fewer Discord "How do I...?" questions
- Fewer GitHub issues about missing/broken docs
- Measurable via Discord/GitHub issue volume

**2. Granular Failure Signals**
- Which specific lines/steps cause drop-offs
- Which sections need improvement
- Context about why failures happen

**3. AB Testing Potential**
- New docs vs old docs
- Which version generates fewer support requests?
- Which version has higher completion rates?

**4. Coverage Gaps Identified**
- Features in codebase without documentation
- APIs missing from reference docs
- Configuration options not documented

### Current Tracking (Limited)

**What They Have**:
- Google Analytics (page-level visits)
- Manual review of Discord questions
- Manual review of GitHub issues

**What They Don't Have** (Yet):
- Session tracking (PostHog or similar)
- Conversion tracking (docs → paid users)
- Completion rate tracking
- Time-on-page with context

**Future Plans**:
- New hire (Prashant) joining to own docs full-time
- Will set up better telemetry and KPIs
- More structured approach to documentation quality

---

## Scope for Pilot Program

### What to Include

**Focus Areas**:
- **Languages**: Python and JavaScript SDKs only
- **Product**: Open source only (exclude cloud, enterprise, pilance)
- **Doc Types**: Getting started guides through advanced tutorials
- **Continuous onboarding**: Not just quickstart - all educational content

**Why This Scope**:
- Limits complexity
- Manageable for initial pilot
- Most users start here
- Python/JS are most common SDKs

**Quote**:
> "we can even limit the scope as in we only care about Python and JavaScript SDKs and we only care about open source right we forget about enterprise forget about cloud everything else and forget about pilance"

### What to Exclude (For Now)

- Rust SDK (more sophisticated, lower-level API)
- Enterprise features
- Cloud-specific documentation
- Pilance (separate file format tool)

### Approach

**Iterative Learning**:
- Start small and discover patterns
- "Even for us it will be new" - expect to learn together
- Make decisions case-by-case as patterns emerge
- Expand scope based on initial findings

---

## Cost & Resources

### Current Documentation Team

**Full-Time Role**:
- Hiring mid-to-senior engineer dedicated to docs
- Not just writing - owning "look and feel, experience"
- One person can own multiple things, so cost is distributed

**Previous Team Member**:
- David (no longer with company)
- Being replaced by Prashant (joining from database partner company)
- Prashant already has context - helped with v2 docs revamp

**Internal Bot Development**:
- Intern building RAG-based bot
- Embeds samples from LanceDB codebase
- Traces questions back to docstrings
- Generates PRs automatically for improvements

### Opportunity Cost

**High Stakes**:
- Docs are "number one product of a dev tool"
- Poor docs = users drop off permanently
- Cost isn't just engineering time - it's lost users

**Investment Justification**:
- Senior person dedicated to docs
- Internal tooling (bots, automation)
- Continuous improvement process
- Critical for user acquisition and retention

---

## Key Insights for Stackbench

### What Stackbench Does Well (Already Built)

✅ **API Signature Validation**
- Catches outdated function signatures
- Validates parameters, types, defaults
- Introspects actual library code

✅ **Code Example Validation**
- Executes code snippets
- Catches syntax and runtime errors
- Validates imports and dependencies

✅ **Automated Testing**
- Exactly what LanceDB wants
- Agent-based approach
- Lower barrier than live user testing

✅ **Parallel Processing**
- Can handle large documentation sets
- Configurable worker count
- Efficient at scale

### What Stackbench Needs to Add/Emphasize

#### 1. ⭐⭐⭐ Granular Failure Location Reporting (CRITICAL)

**Current**: Reports at document level
**Needed**: Reports at line/section/step level

**Example Output Format**:
```
❌ Failed: quickstart.md
   Section: "Creating Your First Table"
   Subsection: "Adding Data"
   Line: 45
   Step: 3 of 5
   Error: ImportError: cannot import name 'Table' from 'lancedb'
   Context: User attempting to create table with pandas DataFrame
```

**Why This Matters**:
- LanceDB can't currently identify specific failure points
- This is their #1 pain point
- Enables targeted improvements

#### 2. ⭐⭐ Missing Coverage Detection (TIER 1 - Partially Built)

**Current**: Detects documented APIs that don't exist
**Needed**: Detects existing APIs that aren't documented

**Implementation Ideas**:
- Scan Python codebase for all public APIs
- Compare against extracted documentation signatures
- Flag APIs with no documentation
- Prioritize by usage frequency (if possible)

**Example Output**:
```
⚠️  Undocumented APIs Found:
   - lancedb.Table.compact() - Public method, no documentation
   - lancedb.Query.with_retry() - Public method, mentioned in code comments but not in docs
   - lancedb.config.set_cache_size() - Configuration option missing from reference
```

**Why This Matters**:
- Users ask "is this even possible?" for features that exist
- Major cause of Discord/GitHub support requests
- Tier 1 priority in original feature plan

#### 3. ⭐ "Clarity" & "Difficulty to Follow" Scoring

**Challenge**: Subjective evaluation
**Approach**: LLM-as-judge

**Evaluation Questions**:
- Were the instructions clear?
- Were prerequisites mentioned?
- Were there logical gaps in the tutorial flow?
- Did the explanation match the code example?

**Example Output**:
```
📊 Clarity Score: 6/10
   Issues:
   - Missing prerequisite: Users need Docker installed (not mentioned)
   - Logical gap: Step 2 references 'config.yaml' not created in Step 1
   - Terminology inconsistency: Uses both "table" and "dataset" for same concept
   Suggestions:
   - Add prerequisites section at top
   - Add Step 1b: Create config.yaml
   - Standardize terminology to "table" throughout
```

**Why This Matters**:
- Not all doc issues are syntax errors
- "Difficult to follow" is a major complaint category
- Requires AI reasoning, can't be done with static analysis

#### 4. ⭐ Continuous Monitoring Mode

**Current**: One-time validation
**Needed**: Recurring validation ("cyclist")

**Features**:
- Schedule regular runs (daily/weekly/monthly)
- Track trends over time
- Alert on new failures
- Diff-based validation (only check changed docs)

**Example Dashboard**:
```
Documentation Health Trends (Last 30 Days)

API Accuracy:    95% → 93% ⚠️  (2 new signature mismatches)
Code Examples:   98% → 98% ✅  (no change)
Missing Coverage: 23 APIs → 19 APIs ✅ (4 newly documented)
Clarity Score:   7.2 → 7.5 ✅  (improved explanations)
```

**Why This Matters**:
- Docs drift as code evolves
- Need ongoing validation, not just at release time
- Proactive catching of issues before users report them

### What They DON'T Need (Yet)

❌ **Real-time User Session Tracking**
- Don't have infrastructure set up
- PostHog/similar not implemented yet
- New hire will work on this later

❌ **Interactive Walkthroughs for Live Users**
- Prefer automated testing first
- Will consider later if automated testing proves value

❌ **Conversion Funnel Optimization**
- Don't track docs → paid user conversions yet
- Future consideration

❌ **AB Testing Infrastructure**
- No current metrics to AB test against
- Could be added after establishing baseline

---

## Recommended Stackbench Roadmap

### Phase 1: Immediate (For LanceDB Pilot)

**Must Have**:
1. ✅ API Signature Validation (already built)
2. ✅ Code Example Validation (already built)
3. 🔧 **Granular Failure Location Reporting** (add line/section context)
4. 🔧 **Missing Coverage Agent** (scan codebase for undocumented APIs)

**Nice to Have**:
5. 🔧 **Clarity Scoring** (LLM-as-judge for "were instructions clear?")
6. 🔧 **Better Summary Reports** (by section, not just by document)

### Phase 2: Short-term (Within Pilot)

7. 📅 **Continuous Monitoring Mode** (scheduled runs)
8. 📅 **Trend Tracking** (document health over time)
9. 📅 **Diff-based Validation** (only validate changed docs)
10. 📅 **Discord Integration** (link failures to actual user questions)

### Phase 3: Long-term (Post-Pilot)

11. 🔮 **Multi-language Support** (TypeScript, JavaScript, Go, Rust)
12. 🔮 **Auto-fix Mode** (agent proposes documentation fixes)
13. 🔮 **GitHub App** (automated PR comments with validation results)
14. 🔮 **Real User Session Tracking** (integrate with PostHog)

---

## Pilot Program Success Criteria

### What Would Make This Successful for LanceDB

**Quantitative Metrics**:
1. **Support Request Reduction**
   - Baseline: Current Discord/GitHub issue volume about docs
   - Target: 20-30% reduction after doc improvements
   - Measurement: Count questions about docs before/after

2. **Coverage Improvement**
   - Baseline: Number of undocumented APIs
   - Target: Document 80% of public APIs
   - Measurement: Coverage report

3. **Accuracy Improvement**
   - Baseline: Number of broken examples/signatures
   - Target: 95%+ accuracy across all docs
   - Measurement: Pass rate from automated tests

**Qualitative Metrics**:
1. **Actionable Signals**
   - Can team easily identify which docs need fixing?
   - Are failure reports specific enough to take action?
   - Do suggested improvements make sense?

2. **Time Savings**
   - How much time saved vs manual doc review?
   - How much faster to identify issues?
   - Reduction in back-and-forth with users?

### What Would Make This Successful for Stackbench

**Happy User Story**:
- LanceDB testimonial about specific improvements
- Quantifiable metrics (reduced support requests by X%)
- Before/after comparison showing doc quality improvement

**Product Validation**:
- Prove automated testing approach works
- Validate that granular signals are valuable
- Demonstrate continuous monitoring value

**Sales Material**:
- Case study with metrics
- Examples of caught issues
- ROI calculation (time/money saved)

---

## Next Steps (From Meeting)

### Action Items

**Richard (Naptha)**:
- Think about how to measure improvements during pilot
- Consider AB testing approach (old docs vs improved docs)
- Prepare for follow-up meeting week of Oct 27

**Ayush (LanceDB)**:
- Prepare pointers on ideal approach based on discussion
- Onboard Prashant (new docs owner) with context
- Set up follow-up meeting with Prashant week of Oct 27

**Both**:
- Define concrete, measurable KPIs
- Ensure KPIs are actually trackable (not vague)
- Finalize pricing for pilot program

### Timeline

- **Oct 21-25**: LanceDB offsite (team unavailable)
- **Week of Oct 27**: Follow-up meeting with Prashant included
- **Post-Oct 27**: Kick off pilot program

---

## Competitive Advantage for Stackbench

### Why Stackbench is Perfect for LanceDB

**1. Solves Their #1 Pain Point**
- Provides granular failure signals they can't get anywhere else
- Line-level, step-level failure identification
- Exactly what analytics can't provide

**2. Automated Agent Approach**
- Lower barrier than live user testing
- Can run continuously as code evolves
- Provides actionable suggestions humans can review

**3. Comprehensive Coverage**
- API signatures + Code examples + Missing coverage
- Not just syntax checking - actual execution testing
- Goes beyond what traditional linters can catch

**4. Built for Continuous Monitoring**
- Not a one-time audit
- Ongoing validation as code evolves
- Proactive issue detection

### Differentiation from Alternatives

**vs. Traditional Linters**:
- Stackbench actually executes code, not just static analysis
- Catches runtime errors, not just syntax errors
- Uses AI to evaluate clarity, not just correctness

**vs. Manual Testing**:
- Scales to hundreds of docs
- Runs automatically and continuously
- No human bias or fatigue

**vs. User Analytics**:
- Shows exact failure points, not just page visits
- Proactive, not reactive
- Catches issues before users complain

**vs. Internal Bots** (like LanceDB's RAG bot):
- More comprehensive (signatures + examples + coverage)
- Actual code execution, not just text matching
- Structured validation output, not just suggestions

---

## Appendix: Meeting Context

### About LanceDB

**Product**: Vector database for AI applications
- Open source, cloud, and enterprise offerings
- Multiple SDKs: Python, JavaScript, Rust
- Related tools: Lance file format, Pylance

**Team**:
- Fully remote (US, Canada, China, India)
- Small but growing engineering team
- CTO, CEO, engineers, community manager in SF

**Recent Changes**:
- Documentation v2 revamp completed
- David (previous docs owner) left
- Prashant joining from database partner company
- Prashant helped with v2 revamp, has existing context

### About Richard/Naptha

**Company**: Building AI agents for developer workflows
**Previous Work**: Onboarding wizards, documentation testing
**Pilot Program**: Originally focused on onboarding wizard
**Pivot**: Shifted focus to documentation testing based on LanceDB feedback

### Meeting Tone

**Collaborative & Exploratory**:
- Both sides learning what's possible
- Willing to adjust scope and pricing
- Focus on finding measurable success criteria
- Honest about current limitations (both sides)

**Alignment**:
- Strong agreement on problem importance
- Shared belief that docs are critical
- Mutual excitement about automated testing approach
- Commitment to making pilot successful

---

## Key Quotes

> "we cannot track user left where user left. They were trying to do something and they could not do it and then they left and then they sort of probably dropped off forever."
> — Ayush on why granular signals matter

> "it's such a nerdy thing to say that an engineer should smile after going through a docs page but I have been there right I know a lot of good docs people who've written good docs page"
> — Ayush on documentation philosophy

> "inaccuracy can be out of date just plain wrong or difficult to follow right or missing steps all of those things"
> — Ayush on types of documentation issues

> "we just had a revamp. so a lot of it might be up to date. but yeah the idea would be that we want to make sure it stays up to date. So kind of a cyclist."
> — Ayush on continuous validation need

> "we can just look at those changes if they make sense right because it's super easy to see that okay yes this was missing and we should have done it this way"
> — Ayush on why automated suggestions are valuable

---

**Document Version**: 1.0
**Last Updated**: October 16, 2025
**Author**: Stackbench Team
**Purpose**: Client discovery documentation for LanceDB pilot program
