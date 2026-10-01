# Brief (verbatim, as issued by Genius Hacks 2026 - do not edit)

## Risk Assessment Workbench
Automating financial crime risk assessment for new products and changes

### The Client
A banking and financial services leader: a large national bank with roughly half
a trillion dollars in assets, spanning consumer banking, commercial banking,
payments and wealth management, closely supervised and examined on how well it
controls financial crime risk.

### The Business Problem
Every time a business unit wants to launch a new product, add a feature, change a
process, onboard a vendor, enter a new geography or open up to a new customer
segment, the Financial Crimes Risk Management (FCRM) function must assess the
financial crime risk it introduces before it goes live. The outcome decides
whether it is approved, rejected, deferred or approved with conditions.

Today that process runs on email, Word, Excel and SharePoint, and depends heavily
on which analyst picks up the case and what they happen to remember. A single
assessment takes fifteen to twenty business days, two analysts can reach
different conclusions on the same change, and when an examiner asks months later
why a risk was rated the way it was, reconstructing the answer is slow and often
incomplete.

### What They Want Built
A Risk Assessment Workbench: one governed platform that carries a change request
from intake through assessment to a committee decision, replacing the email and
spreadsheet trail. Workflow, scoring and record-keeping are automated. AI is
applied where it earns its place, typically finding relevant policy, pulling
structure out of submitted documents and drafting the assessment for review. It
serves three groups: a product owner who raises the change, an FCRM analyst who
finalises the assessment and owns platform configuration, and a risk committee
that votes on the result.

### What Good Looks Like
- Intake to decision-ready in around two days, against fifteen to twenty today
- Every rating traceable to its inputs and reasoning
- Foundational data for AI: a modelled, governed data layer the system can actually reason over
- Scoring parameters and workflow rules tunable by the risk function
- An immutable audit trail that can be handed to an examiner
- The system prepares, humans decide. Nothing is approved or rejected automatically

### Constraints Worth Knowing
- Risk decomposition grounded in published supervisory frameworks, not invented. Finding the right ones is part of the exercise
- Controls mitigate risk; they never eliminate it. Scoring must respect that
- A human can disagree with any system output, record why, and have the consequences handled
- Synthetic data only. No connection to any real system

### Deliberately Not Specified
- Which parts of the workflow are automated, which use AI and which stay manual
- How risk is scored
- Where the human checkpoints sit
- Which stack you use
