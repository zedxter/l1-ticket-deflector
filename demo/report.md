# L1 Ticket Deflector - demo run report

```
======================================================================
  L1 TICKET DEFLECTOR - DEMO RUN REPORT
======================================================================

  RESULTS ON THE DEMO DATASET
  ------------------------------------------------------------------
  Tickets processed         : 45
    [AUTO] Resolved          : 25
    [HUMAN] Escalated        : 18  (high/critical sensitivity)
    [QUEUE] No match         : 2  (general L1 queue)

  Deflection rate (sample)  : 55.6%
  Decision accuracy         : 100.0%  (auto/escalate/queue correct)
  Routing accuracy          : 100.0%  (correct KB article)

  ------------------------------------------------------------------
  HONEST ROI MODEL (conservative DACH assumptions)
  ------------------------------------------------------------------
  Company                   : ~500 employees
  L1 tickets per month      : ~1200
  Deflection (conservative) : 30%  (market: 20-40%)
  Avg manual handling time  : 19 min
  IT specialist rate        : 45 EUR/hour (fully loaded)

  Auto-resolutions / month  : ~360
  Time saved                : ~114 h/month  (~0.7 FTE)
  Client savings            : ~5,130 EUR/month
  Retainer                  : 4,000 EUR/month
  ROI                       : x1.3 per month (x15 per year)

  ------------------------------------------------------------------
  PER-TICKET BREAKDOWN
  ------------------------------------------------------------------
  [AUTO ] T-1001 -> KB-001 | I forgot my domain password, can't log into Windows 
  [AUTO ] T-1002 -> KB-001 | Hi, I need to reset my domain password please
  [AUTO ] T-1003 -> KB-003 | VPN not working, AnyConnect shows an authentication 
  [AUTO ] T-1004 -> KB-004 | VPN keeps disconnecting every 10 minutes, impossible
  [AUTO ] T-1005 -> KB-005 | How do I install 7-Zip? I need an archive program
  [HUMAN] T-1006 -> KB-006 | Please install non-standard 3D modeling software, th
  [AUTO ] T-1007 -> KB-007 | Printer in accounting won't print, jobs stuck in the
  [HUMAN] T-1008 -> KB-008 | I need access to the marketing team's network folder
  [AUTO ] T-1009 -> KB-009 | My account is locked, too many failed login attempts
  [HUMAN] T-1010 -> KB-010 | I don't get the MFA code on my phone, can't confirm 
  [AUTO ] T-1011 -> KB-011 | Very slow Wi-Fi in the office on the third floor
  [HUMAN] T-1012 -> KB-012 | Please issue a new laptop to replace the broken one,
  [AUTO ] T-1013 -> KB-013 | How do I set up work email on my iPhone?
  [HUMAN] T-1014 -> KB-014 | Need to buy an Adobe Acrobat license for a new emplo
  [HUMAN] T-1015 -> KB-015 | Tomorrow is a new developer's first day, need full o
  [AUTO ] T-1016 -> KB-016 | Microsoft Teams won't launch, the window freezes on 
  [AUTO ] T-1017 -> KB-017 | Only 2 GB left on drive C:, the system is slow
  [HUMAN] T-1018 -> KB-018 | I accidentally deleted important files from the proj
  [HUMAN] T-1019 -> KB-019 | I received a suspicious email with a link, looks lik
  [AUTO ] T-1020 -> KB-020 | External monitor not detected through the docking st
  [AUTO ] T-1021 -> KB-001 | password reset
  [AUTO ] T-1022 -> KB-001 | password reset for my domain account, urgent
  [HUMAN] T-1023 -> KB-002 | I need root access to the server, please change the 
  [AUTO ] T-1024 -> KB-003 | VPN won't connect from my home internet, what should
  [AUTO ] T-1025 -> KB-005 | How do I install VS Code on my work laptop?
  [AUTO ] T-1026 -> KB-007 | Printer offline in the sales department, please help
  [HUMAN] T-1027 -> KB-010 | I lost my work phone with the Authenticator app, MFA
  [AUTO ] T-1028 -> KB-017 | Please increase my disk quota, more than 20 GB
  [HUMAN] T-1029 -> KB-019 | I suspect a hack: I got a notification about a login
  [HUMAN] T-1030 -> KB-008 | Need edit rights in SharePoint for a joint project
  [AUTO ] T-1031 -> KB-013 | outlook mobile setup on android device
  [HUMAN] T-1032 -> KB-012 | Want to approve the purchase of a 27-inch monitor fo
  [AUTO ] T-1033 -> KB-011 | Wi-Fi speed is terrible, pages take forever to load
  [HUMAN] T-1034 -> KB-014 | Need a license for a team seat, ran out of seats
  [HUMAN] T-1035 -> KB-010 | I don't get the OTP email, I lost my phone — urgent,
  [AUTO ] T-1036 -> KB-007 | How do I check the toner level and clear the print q
  [AUTO ] T-1037 -> KB-017 | Disk is full, the computer won't save files
  [HUMAN] T-1038 -> KB-008 | Lost access to a folder, rights disappeared after va
  [HUMAN] T-1039 -> KB-019 | Ransomware on my laptop!!! files renamed to .locked,
  [AUTO ] T-1040 -> KB-020 | Second screen won't turn on, can't extend the deskto
  [QUEUE] T-1041 -> -      | I have a question about the coffee machine in the of
  [QUEUE] T-1042 -> -      | I'd like to know about corporate gym discounts
  [AUTO ] T-1043 -> KB-011 | I think internet speed dropped, but not sure, please
  [AUTO ] T-1044 -> KB-007 | Can't print a PDF, the printer shows a driver error
  [HUMAN] T-1045 -> KB-008 | Please revoke a departed employee's access urgently

======================================================================
  Demo: keywords + stemming (no LLM). Production version - LangGraph:
  RAG over the KB, tool-calls into ITSM, human-in-the-loop, telemetry.
======================================================================
```
