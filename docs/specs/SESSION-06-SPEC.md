# SESSION 06 — Education, Healthcare & Human Development Engine (owner spec, received 2026-11-21)

Gate rule: starts only after Session 05 is fully implemented + tested. Reuse Sessions 01–05; never recreate. Every unit: real logic, persistent data, verified behaviour. Dashboards = data layer over persistent records only.

## Education framework
Configurable per country: national policies, regional authorities, education ministry, public/private/community education, funding, quality standards, academic calendars.

## Institutions
Kindergartens, primary/secondary/high schools, colleges, universities, technical institutes, vocational centres, research institutions, professional academies. Each: ID, location (real city building), capacity, departments, teachers, students, facilities, operational budget, academic performance, infrastructure condition.

## Student journey
Enrol → attend → assignments → examinations → skill development → grades → level progression → graduate → dropout only when circumstances justify → further education. Outcomes driven by attendance, learning opportunities, resources, individual characteristics, educational support. NO arbitrary grade generation.

## Teachers
Recruitment, qualifications, teaching assignments, work schedules, salary payments (ledger), performance evaluations, professional development, academic responsibilities; interact with students via simulated educational activities.

## Curricula (configurable data)
Subjects: mathematics, science, languages, technology, engineering, arts, humanities, vocational, professional training. Each: learning objectives, required skills, difficulty, duration, assessment criteria, prerequisites. Learning outcomes change real knowledge/skills.

## Examinations & records
Class tests, assignments, practical assessments, semester/final examinations, professional assessments, graduation requirements. Persistent academic records.

## Careers link (Session 04)
Skill acquisition/improvement, qualifications, certifications, career pathways/changes, professional experience, lifelong learning. Education + experience influence job eligibility and salary opportunities (existing credential gates are the foundation — extend, don't duplicate).

## Healthcare network
Clinics, community health centres, general/specialised hospitals, emergency departments, diagnostic centres, rehabilitation centres, pharmacies, public health institutions. Each: staff, capacity, equipment, services, operating budget, patient capacity, condition. (District 1 reality: a clinic, per GDD-12 — grow the network honestly from the data.)

## Health model
Track: general condition, fitness, nutrition, sleep, stress, age-related change, injuries, illness, recovery, disability where relevant. Responds to environmental + lifestyle factors. Configurable SIMPLIFIED rules — never claim clinical accuracy. Extends GDD-12's condition layer; do not duplicate it.

## Disease simulation
Communicable + noncommunicable models, infection transmission, recovery, immunity assumptions, vaccination, healthcare capacity pressure, epidemic monitoring, public health interventions. Configurable epidemiological parameters. Scenario outputs are NOT real medical predictions.

## Patient journeys
Registration → appointment → assessment → diagnostics → treatment plan → medication → admission → discharge → follow-up → recovery records. Every treatment connected to healthcare resources + financial systems.

## Medication & pharmacy
FICTIONAL simulated medication inventory: procurement, hospital stock, pharmacy operations, prescription fulfilment, shortages, distribution logistics. Availability affects care. Never represent as a real prescription service.

## Life-stage care
Prenatal, maternal, birth-related, infant, child, adolescent, adult, elderly, long-term care — connected to Session 01 life-cycle events (births already occur in-sim).

## Wellbeing
Stress, social support, loneliness, emotional wellbeing, work-life balance, family conditions, community participation, support-service access — connected to Session 01 emotions + Session 02 social systems. Do NOT diagnose real-world medical conditions.

## Healthcare economics (Sessions 04/05)
Hospital budgets, public healthcare funding, private expenditure, insurance simulation, medical costs, workforce salaries, public health spending, financial accessibility. Healthcare responds to available resources. (Note: care is currently civic/unpriced per GDD-12 — any pricing must be an explicit, labelled model decision, not a silent invention.)

## Research ecosystem
University + medical research, laboratories, technology development, research funding, academic publications as simulated records, collaboration, innovation transfer. Outcomes influence technological/institutional development via configurable rules (feeds Session 10 technology progression).

## Human development indicators (documented assumptions)
Literacy, educational access, graduation rates, skill distribution, healthcare accessibility + capacity, life-expectancy estimates, population health indicators, research activity, HDI.

## Performance
Event-driven learning progression, scheduled academic events, efficient health updates, aggregated population health, background epidemic simulation, batch examinations, resource-aware hospital operations. Never process every student/patient continuously.

## Acceptance criteria (all must be test-verified)
1 Institutions operate. 2 Students enrol + progress. 3 Teacher assignments function. 4 Learning changes skills. 5 Examinations produce consistent outcomes. 6 Graduates become eligible for relevant careers. 7 Healthcare facilities have capacity constraints. 8 Patient journeys work. 9 Medical inventory affects treatment availability. 10 Health changes persist. 11 Epidemic scenarios work. 12 Public healthcare budgets remain consistent. 13 Research records persist. 14 HDI calculated correctly per documented method. 15 Previous sessions remain operational.

Report: completed units, files, DB changes, simulation logic, API changes, test results, benchmarks, limitations, remaining work. Do NOT start Session 07 until Session 06 passes.
