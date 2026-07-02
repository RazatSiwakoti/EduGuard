 
KINGS OWN INSTITUTE · INFORMATION TECHNOLOGY DEPARTMENT · MIT CAPSTONE

 
EdGuard 
Proactive Academic Risk Monitoring and Intelligent Support Platform Using Machine Learning
Early Detection. Timely Action. Better Outcomes


Project Proposal 
Submitted by:
Luis Miguel Palafox (20032513)
Razat Siwakoti (20032655)
Manish Thapa Magar (20032890)
Aashutosh Budhathoki (20032618)
Fardeen Ali Mohammed (20033451)

King’s Own Institute (KOI)
Master of Information Technology
ICT728 – Capstone Project 1
Date: April 2026

 
Executive Summary
King’s Own Institute (KOI) is a tertiary-level institution offering high-quality courses based in Sydney and Newcastle, Australia. Their aim is to make sure students are nurtured and ready for their future careers (KOI – King’s Own Institute – Success in Higher Education n.d.).
Despite the presence of learning management systems like Moodle, the process of identifying those in trouble or "Students-at-Risk" remains largely manual. This approach is time-consuming and inefficient, particularly with the limited number of resources of educators that manage a large amount of the student population.
The proposed solution, EdGuard, is a dashboard-like web application that the educators can access and import relevant student information to determine which enrolled students require any help. Along with an automated warning message that would grab the attention of the “Student-At-Risk” and for the professor to take action accordingly rather than having the process of them combing through all the student lists.
 
Table of Contents
1. Introduction	1
2. Vision Statement	1
3. Goals and Objectives	1
3.1 Deliverables	2
4. Project Scope	3
5. Project Plan	4
5.1 Project Design Methodology	4
5.2 Project Timelines	4
5.2.1 Sprint Milestones	6
5.2.2 WBS and Gantt Chart	9
5.3 Technical Approach and Methodology	15
5.3.1 Data Pipeline	15
5.3.2 Core Detection Engine – Hybrid Model	15
5.3.3 Explainability, Notifications and Prototyping	16
5.4 Advanced Technologies	17
6. Project Team	18
7. Conclusion	20
8. Recommendations	20
References	22






 
1. Introduction
KOI has a numerous amount of students studying in a single trimester, with each trimester having around 20 to 30 students per class in a scheduled time. One educator can handle up to two or three classes during these terms, meaning a single educator may manage an estimated 60 to 90 students per term. This makes it difficult for lecturers to keep track of all enrolled students and can consume more time to check papers, which they should spend to ensure each student is up to par with the lessons.
2. Vision Statement
“To reduce preventable student failure at King’s Own Institute by developing an automated, explainable, and scalable machine learning system that identifies at-risk student weeks before failure, enabling timely, data-driven intervention and improved academic outcomes.”
 3. Goals and Objectives
The purpose of the study is to address the tedious amount of workload from lecturers, enabling them to focus on more important tasks such as lectures and other administrative duties that contribute to higher quality learning environment. It also aims to ensure students are aware of their academic standings during the term so they can focus on topics where they are lacking.
The study proposes EdGuard - an online website application dashboard that clearly shows the number of students which are currently enrolled under each educator, displaying both who are performing well alongside those who aren’t. The dashboard is filterable by Subject Code, Lecture Time and Term. The system would also have a section that tells how many students have been sent a letter of caution, including class they belong to and  their subject code. In addition to these features, we would apply machine learning to apply prescriptive analytics to the class so that the professor will have an early indicator based on the student’s pattern that could pose a risk,  opening more proactive intervention hence improving institutional performance in the long run. It will, henceforth, reduce the time needed for administrative tasks such as manually checking student one by one and sending emails. It will also give proactive insights to students that may need future assistance by giving them tips at the disposal of the professor such as guidance counselling, or even other branches such as finance depending on what the student needs and the available facilities in the institution. These steps will lessen, if not eliminate, the possibility of at-risk students failing, giving quality and supportive education to students, and better satisfaction to the faculty and the business. It will also aid in competitive edge towards other institutes hence gaining profitability saving time for lecturers who are already spread thin during classes as they can focus more on the class itself than trying to manage the class.
3.1 Deliverables
The following deliverables will be produced and handed over to the KOI IT Department upon project completion:
Table 1: Project Deliverables upon completion
#	Deliverable	Description
1	Standardized Excel Data Template	A clean, validated input template for student collection across all subjects 
2	Automated Risk Detection System (EdGuard)	Hybrid rule engine and ML classification pipeline identifying at-risk student across three levels: High Risk, At Risk and Safe
3	React Web Dashboard	Browser based interactive dashboard for authorized staff, filterable by subject, class, day and term
4	Automated Email Notifications	Personalized student notifications dispatched automatically at Week 4 and Week 8 checkpoints. Zero manual staff effort required.
5	Consolidated At-Risk Report 	Downloadable report consolidating at-risk student data across all subjects for staff review and records.
6	ML Model Performance Report	Comparison of all five classification models with F1-score results and justification for the final model selected.
7	SHAP Explainability Output	Per-student risk explanations identifying the top contributing factors for every at-risk prediction.
8	Source Code and Documentation	Complete codebase with setup guide, user manual, and developer documentation for future maintenance.
4. Project Scope
The following outlines the boundaries of EdGuard, defining what is included in and excluded from the scope of development to ensure aligned expectations:
INCLUSIONS
	Attendance, tutorial, and assessment data analysis
	Standardised Excel input template design
	Hybrid rule-based and ML detection engine
	Five ML classification models trained and evaluated
	SHAP explainability for all ML predictions
	SMOTE class balancing for training data
	React web dashboard for authorised staff
	Automated SMTP email notifications
	Week 4 and Week 8 automated scheduling
	Risk tracking with Week 9 final update

EXCLUSIONS
	Direct student counselling or intervention
	Predictive analytics beyond Week 8
	Modification of KOI's Moodle system
	Student grade management
	Mobile application development
	Third-party system integration
	Financial or welfare service management
	Historical data beyond current trimester
 
5. Project Plan
5.1 Project Design Methodology
Given the data needed for such a project it is with careful consideration that the Method used to build the Application would be Agile, this will keep the client invested without wasting time and achieve needed requirements such as Data that will be used in Machine Learning and in the Application Proper, Agile Methodology is widely used in the industry for builds that could include iterations such as sprints which gives point to point checkpoints and customer feedback assuring satisfaction and even enhancements or ideas along the way, though the drawbacks could be ballooning of requirements there are countermeasures that can be taken through negotiations to lessen this problem, like in a case study by (Younas et al. 2020) the researchers weren’t able to apply agile methodology fully because of some problems such as “face-to-face communication, availability of experts, smooth control of development, ability to build applications from distributed locations, and resource management.” These problems on a larger scale can be feasible and easily manageable in a small-scale project and adapting would be easy once it scales up.
5.2 Project Timelines
The project is executed in two semesters based on Agile Scrum (Kalyani and Mehta, 2019), and it consists of four three-week sprints. Project 1 will be 2 March to 18 May 2026 (Sprints 1 and 2), and Project 2 will be 29 June to 14 September 2026 (Sprints 3 and 4). We have a week of review and retrospective after our sprints to analyze the progress and reflect the backlog of the next sprint.
The pre-sprint planning phase is every first two weeks of each semester. This is the time to develop or enhance the product backlog, develop and prioritize user stories, and download and process the Kaggle data to be utilized. This will take care of the fact that development work in every sprint will have clearly defined goals and clean data.
Sprint 1 is dedicated to the data underpinning, developing the standardized Excel input template, cleaning and preprocessing the Kaggle data, and the first rule-based risk engine development. A simulated Week 4 checkpoint is carried out at the end of Sprint 1 to ensure that the at-risk identification is operational. The Sprint 2 builds upon this platform by applying the concept of multi-subject data aggregation, the use of automated email notification through SMTP, and student risk status monitoring between Week 4 and Week 8 checkpoints.
Sprint 3 of Semester 2 exposes the machine learning pipeline, such as SMOTE class balancing, training and evaluating various classification models (Logistic Regression, Random Forest, XGBoost, and SVM), integrating the hybrid rule-based and ML engine, and exposes the predictions via Fast API endpoints. Sprint 4 builds on the system and introduces SHAP explainability, the React front-end dashboard, personalized student notifications, and full system integration testing. In Week 12 of Semester 2, the project is finalized by submitting the final system, consolidated at-risk report and all other supporting documentation.
According to project requirements of KOI, the records of at-risk students will be tracked and updated using two fixed checkpoints that will be simulated at Week 4 and Week 8 of each semester.
The task is categorized based on the technical parts with task responsibilities allocated to team members. Each task has designated lead responsible for delivery, supported by associated team members where applicable.
 
5.2.1 Sprint Milestones
The following details are the key deliverables and milestones achieved at each sprint and checkpoint throughout the project lifecycle:
SEMESTER 1 – PROJECT 1 (2 MARCH – 22 MAY 2026)
10 Mar (W2) - Backlog & User Stories    Pre-Sprint Planning
	Finalised product backlog with all requirements listed and prioritised
	User stories written for Sprints 1 and 2 (with acceptance criteria)
	Sprint 1 backlog assigned to team members

17 Mar (W2-W3) - Sample Dataset Collection    Pre-Sprint Planning
	Kaggle dataset downloaded and stored
	Initial exploratory data analysis (EDA) completed
	Standardised Excel input template (v1) designed and ready for data entry

7–10 Apr (W5 -W6) - Sprint 1 Milestones     Sprint 1 
	Rule-based risk engine operational (flags students with <50% attendance, missed assessments, <50% tutorial submission)
	Week 4 checkpoint run successfully — at-risk students identified
	Sprint 1 review completed and Sprint 2 backlog refined

5 May (W9) - Checkpoint 2  Sprint 2
	Multi-subject data consolidation module working
	Automated SMTP email notifications tested and dispatched to at-risk students
	Risk status tracking updated for Week 8 checkpoint

8 May (W10) - Sprint 2 Review  Sprint 2
	Automated notification system fully reviewed and validated
	Status tracking alerts confirmed working
	Sprint 2 retrospective completed with documented lessons learned

22 May (W12) - Final Project 1 Submission    End of Semester 1
	Clean, standardised Excel template (final version)
	Automated at-risk identification system
	Consolidated at-risk report across all subjects
	Automated notification logs showing messages sent to students
	Week 4 and Week 8 status tracking records
	Full project documentation and handover notes for Semester 2

 
29 Jun – 8 Jul (W1–W2) — Pre-Sprint Refinement   Pre-Sprint Planning
	Product backlog updated and refined based on Semester 1 outcomes
	User stories with defined acceptance criteria developed for Sprints 3 and 4
	Dataset pre-processed and expanded for machine learning
	Prototype dashboard designed and validated
SEMESTER 2 – PROJECT 2 (29 JUNE – 12 SEPTEMBER 2026)

9 Jul – 1 Aug (W3–W5) — Sprint 3: Machine Learning Development  Sprint 3
	Data preprocessing and feature engineering pipeline completed
	SMOTE applied to address class imbalance in the dataset
	ML models trained and evaluated (Logistic Regression, Random Forest, XGBoost)
	Best performing model selected based on evaluation metrics
	Hybrid rule-based and ML solution developed
	FastAPI backend created for predictive services

9 Aug – 25 Aug (W7–W8) — Sprint 4: System Development & Integration Sprint 4
	SHAP explainability integrated into the system
	Interactive React dashboard developed
	Automated email notification system implemented
	Full system integration completed (frontend, backend, ML)
	System QA and integration testing conducted

26 Aug – 3 Sep (W9) — Sprint 4 Review & Testing Sprint 4
	Week 8 simulation checkpoint successfully executed
	End-to-end system testing and debugging completed
	System performance validated
	Sprint 4 retrospective completed with final improvements


4 Sep – 12 Sep (W10–W11) — Final Project 2 Submission End of Semester 2
	Final system optimised and deployment-ready
	Consolidated at-risk report generated
	Dashboard fully functional with real-time insights
	Notification logs verified and validated
	Complete project documentation finalised

5.2.2 WBS and Gantt Chart
EdGuard Project 1 – Semester 1
 
Figure 1: EdGuard - Project 1 WBS
 
 

 

 
Figure 3: EdGuard - Project 1 Milestones
   
EdGuard Project 2 – Semester 2
 
Figure 4: : EdGuard - Project 2 WBS
 
 


 











 

 
5.3 Technical Approach and Methodology
EdGuard will be delivered as a full-stack application comprising a React-based frontend dashboard, a Python-based ML backend, and a prototyping layer for client validation prior to full development.
5.3.1 Data Pipeline
The raw student data is obtained from Kaggle, and the data goes through little modification because the dataset has features that is not used by KOI to grade the student. For example: online forum participation column is changed to weekly tutorial. The data passes through a structed preparation before any modeling occurs - ) Data Ingestion — loading the standardized Excel template via Pandas; (b) Preprocessing — handling missing values, duplicates, and noise; (c) Exploratory Data Analysis (EDA) — understanding distributions and feature relationships; and (d) Class Balancing via SMOTE — generating synthetic at-risk examples to correct the anticipated class imbalance in the dataset.
5.3.2 Core Detection Engine – Hybrid Model 
EdGuard's detection engine combines two independent layers. The Rule-Based Engine checks hard thresholds: attendance below 50%, tutorial submission rate below 50%, failing tutorial scores, or any missed overdue assessment, assigning weighted risk scores and flagging obvious cases immediately. The ML Classification Engine handles borderline cases by detecting patterns across multiple metrics that do not individually breach any threshold. Five models are evaluated — Logistic Regression (baseline), Decision Tree, Random Forest, XGBoost, and SVM — with the model achieving the highest F1-score selected for production.
Table 3: Hybrid Decision Logic
Rule-Engine	ML Model	Final Outcome	Reason
Flag	Flag	High Risk	Both layers agree — maximum certainty
Flag	Safe	Flagged	Hard threshold breach is non-negotiable
Safe	Flag	Review	ML detected a pattern — human review required
Safe	Safe	Safe	Both agree — no action required

 
5.3.3 Explainability, Notifications and Prototyping
SHAP is used as an XAI(explainable AI) to every ML prediction, identifying each feature’s contribution to the individual risk classification, making every decision transparent and auditable. Personalized email notifications are sent automatically to students via SMTP at Week 4 and Week 8 checkpoints using APScheduler, with zero manual staff effort. Prior to full deployment, Figma and Altair will be used for prototyping dashboards and ML outputs respectively.
5.4 Advanced Technologies
Table 4: Advanced Technologies Usage
Technology	Layer	Purpose
Python 
(Pandas, Sckit-learn, OpenPyXL)	Core/ML	Primary Language for data processing, ML pipeline and backend logic
SMOTE	Data Engineering	Correct class imbalance by generating synthetic training examples without data loss
ML Models
(Decision Tree, Random Forest, XGBoost, Logistic Regression, Support Vector Machine(SVM)	ML	ML models trained and compared for prediction. Best selected by weighted F1-score.
Hyperparameter Tuning
Grid Search	ML Optimization	Identification for optimal configuration of model
Multi-Class Classification	ML Design	Three output classes :High Risk, At Risk, Safe . Evaluated by weighted F1-score.
K-Fold Cross-Validation	ML Validation	Produces a reliable performance estimate across multiple data splits.
SHAP	Explainable AI	Calculates each feature's contribution to every prediction — full transparency (XAI).
FastAPI	Backend	Exposes the ML pipeline as REST endpoints consumed by the React dashboard.
APScheduler	Backend	Auto-triggers risk detection and email dispatch at Week 4 and Week 8 checkpoints.
SMTP (smtplib)	Backend	Send personalized emails to identified at-risk students.
React	Frontend	Interactive web dashboard communicating with backend via REST API.

 
6. Project Team
The following table defines task responsibilities and team allocations for EdGuard. Each task has a designated lead responsible for delivery, supported by associated team members where applicable.
Task	Leader	Associated Members
Project Management
Overall coordination, timeline, client communication, project reviews	Luis M. Palafox	All team members
ML Pipeline Development
Data preprocessing, SMOTE, model training (DT, RF, XGBoost, LR, SVM), hyperparameter tuning, cross-validation, model selection	Razat Siwakoti 	Luis M. Palafox,
Manish Thapa Magar
Rule-Based Engine Development
Risk scoring logic, threshold rules, weighted flag system, hybrid decision logic	Razat Siwakoti	Luis M. Palafox

Backend API Development
FastAPI endpoints, SMTP notifications, APScheduler checkpoint automation	Manish Thapa Magar	Razat Siwakoti

Frontend Dashboard Development
React web application, dashboard UI, REST API integration, data visualization	Aashutosh Budhathoki	Luis M. Palafox,
Fardeen Ali Mohammed
Prototyping 
Figma dashboard mockup, Altair ML output simulation	Aasutosh (frontend),
Luis M. Palafox (Backend)	All team members

Documentation
Technical Documentation	Fardeen Ali Mohammed	All team members
Testing and Quality Assurance
Integration testing, ML validation, end-to-end testing 	Fardeen Ali Mohammed	All team  members
Table 5: Task Allocation


Table 6: Team Member Summary
Team Member	Primary Role	Key Responsibilities
Luis M. Palafox	Project Leader and System Architect	Project planning, coordination, architecture design, integration oversight
Razat Siwakoti	Machine Learning Engineer	Data processing, ML pipeline, rule engine, evaluation, SHAP, SMOTE
Aashutosh Budhathoki	Frontend Developer	UI/UX design. React dashboard development, Figma Prototyping, API integration
Manish Thapa Magar	Backend Developer	API development, SMTP notifications, APScheduler checkpoint automation
Fardeen Ali Mohammed	Testing and QA Engineer, Technical Documentation Lead	Unit/integration Testing, UI/UX Testing, Technical writing, validation, Quality Assurance


 
7. Conclusion
The increasing number of students at King’s Own Institute (KOI) has made it difficult for the educators to identify students who are at risk of academic failure. The system has to involve a process of student performance tracking, which is time-consuming and can easily leave out critical information since one lecturer has to handle around 60-90 students every trimester. The gap in early intervention is likely to give rise to two negative consequences, which are academic performance for students and administrative responsibilities for teachers. The project will create a student-at-Risk Dashboard web-app, which will be able to integrate with Moodle data. The solution will give all student performance information to all tutors and lecturers through one web-app, which will make it easy for them to identify students who are at risk and communicate with them through email about their in-risk status. The system will use machine learning and prescriptive analytics to monitor students’ status. The automated alert will improve the system since it will require minimal work, yet it will alert students (Nimy, Mosia & Chibaya 2023).
This dashboard will reduce the amount of work, which will enable the tutors and lecturers to concentrate on teaching and mentoring the students. This will enable KOI to have better performance in terms of student retention, hence enhancing its ranking by the Australian Government based on the performance of the students in the tertiary education sector.
This project is developed over a period of two trimesters. In the first trimester (ICT728), the team will finalize the project scope, undertake literature and technology reviews, design the system, and implement the working prototype, which will have at least one key feature of the dashboard. In the second trimester (ICT729), the team will build on what is developed in the first trimester to implement the entire system. This is done to ensure that each stage is well thought through before moving on to the next stage.
8. Recommendations
This Student-at-Risk project is expected to succeed and operate efficiently by following the recommendations which arose from the current KOI current challenges assessment and proposed solution in the five Automation of Student at Potential Risk Management provided by KOI. The KOI stakeholders must start engaging closely with the project team from the early phase. The dashboard development will need close collaboration of the project team with academic staff and IT personnel so they are able to create operational workflows which will allow the project team to have all the necessary data while still protecting the privacy rights of the students. The team will use Agile development to better define its sprint objective which will help them complete the project goals and requirements (Younas et al. 2020). The system needs to have data safety laws in place to comply with all the data protection laws under the Privacy Act 1988 by the Australian government (Privacy Act 1988).
Before full launching of the Webapp, the project team has  to test the Webapp in a pilot phase with a limited group of students so they can check the functionality of the system , gather feedback from the lecturers and identify any  issues. Finally, the system should also  be designed with scalability in mind, as KOI is a continuously growing educational institute the system might need to add things like student counseling and financial support services in the future . 
The student-at-risk dashboard gives a practical response to a challenge within KOI. With a structured two-trimester delivery plan, proper data handling and stakeholder engagement at every required phase, this project has huge potential to improve student support and efficiency across the institution
 
References
KOI – King’s Own Institute – Success in Higher Education n.d., koi.edu.au.
Kalyani, D. and Mehta, D. (2019). Study of Agile Scrum and Alikeness of Scrum Tools. International Journal of Computer Applications, 178(43), pp.21–28. doi:https://doi.org/10.5120/ijca2019919318.
Nimy, E, Mosia, M & Chibaya, C 2023, 'Identifying at-risk students for early intervention — A probabilistic machine learning approach', Applied Sciences, vol. 13, no. 6, p. 3869, DOI: 10.3390/app13063869.
Office of the Australian Information Commissioner 2025, The Privacy Act, OAIC, viewed 2 April 2026, https://www.oaic.gov.au/privacy/privacy-legislation/the-privacy-act.
Younas, M, Jawawi, DNA, Mahmood, AK, Ahmad, MN, Sarwar, MU & Idris, MY 2020, ‘Agile Software Development Using Cloud Computing: A Case Study’, IEEE Access, vol. 8, pp. 4475–4484.

