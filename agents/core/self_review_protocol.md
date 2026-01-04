# Self-Review & Human Checkpoint Protocol

This protocol must be added to the END of every agent's workflow.

## When to Use
After the agent completes its MAIN WORK, before dismissing.

## The Protocol

```xml
<self-review-protocol>
    <!-- PHASE 1: Self-Review -->
    <step n="1" name="SELF-REVIEW">
        Review your own output. Ask yourself:
        - What information is MISSING but would add value?
        - What names/places/dates need more investigation?
        - What claims did I make without strong sources?
        - What could lead to discovering another related case/story?
        - What would a skeptical viewer question?
    </step>
    
    <!-- PHASE 2: Generate Questions -->
    <step n="2" name="GENERATE-QUESTIONS">
        Generate 10 questions about gaps in your work:
        
        Display:
        ```
        📋 SELF-IDENTIFIED GAPS (10 Questions I Couldn't Fully Answer):
        
        1. {Question about missing person/name}
        2. {Question about unverified claim}
        3. {Question about potential sub-investigation}
        4. {Question about alternative angle}
        5. {Question about missing source}
        6. {Question about connection to other cases}
        7. {Question about victim/affected party}
        8. {Question about timeline/dates}
        9. {Question about official response}
        10. {Question about what happens next}
        ```
    </step>
    
    <!-- PHASE 3: End Menu -->
    <step n="3" name="END-MENU">
        Display the END MENU:
        ```
        ════════════════════════════════════════════════════════
        🔍 SELF-REVIEW COMPLETE | Ready for Human Checkpoint
        ════════════════════════════════════════════════════════
        
        I have identified areas that could strengthen this work.
        
        OPTIONS:
        [1] 🔄 SUB-INVESTIGATE - Let me search for answers to my 10 questions
        [2] ✏️ MANUAL INPUT - You have additional questions/instructions for me
        [3] ✅ PROCEED - Skip to next agent, I'm satisfied with current output
        
        ════════════════════════════════════════════════════════
        ```
        
        WAIT for user input.
    </step>
    
    <!-- PHASE 4: Process User Choice -->
    <step n="4" name="PROCESS-CHOICE">
        IF user selects [1] SUB-INVESTIGATE:
            - Take each of your 10 questions
            - Use ANY available tool to find answers:
              - google_web_search
              - youtube_search.py
              - caption_reader.py
              - web_reader.py
              - article_screenshotter.py
              - link_checker.py
            - UPDATE your output file with new findings
            - Mark new findings as "[SUB-INVESTIGATION FINDING]"
            - Return to STEP 2 (generate new questions if needed)
        
        IF user selects [2] MANUAL INPUT:
            - Ask: "Enter your questions or instructions:"
            - Process the user's input like a new investigation
            - Use any tool needed to find answers
            - UPDATE your output file with new findings
            - Return to STEP 2 (generate new questions if gaps remain)
        
        IF user selects [3] PROCEED:
            - Confirm: "✅ Work complete. Ready for next agent."
            - Dismiss agent
    </step>
</self-review-protocol>
```

## Tools Available to ALL Agents

Every agent has access to these tools when needed:

| Tool | Command | Purpose |
|------|---------|---------|
| Google Search | `google_web_search` | Search for any information |
| YouTube Search | `python {video_nut_root}/tools/downloaders/youtube_search.py --query "{query}"` | Find videos |
| Video Transcript | `python {video_nut_root}/tools/downloaders/caption_reader.py --url "{url}"` | Get video captions |
| Find Quote Timestamp | `python {video_nut_root}/tools/downloaders/caption_reader.py --url "{url}" --find-quote "{quote}"` | Find exact timestamp |
| Web Page Text | `python {video_nut_root}/tools/downloaders/web_reader.py --url "{url}"` | Extract article text |
| PDF Text | `python {video_nut_root}/tools/downloaders/pdf_reader.py --file "{path}"` | Extract PDF content |
| URL Validator | `python {video_nut_root}/tools/validators/link_checker.py "{url}"` | Check if URL is valid |
| Screenshot | `python {video_nut_root}/tools/downloaders/screenshotter.py --url "{url}" --output "{path}"` | Basic screenshot |
| Quote Screenshot | `python {video_nut_root}/tools/downloaders/article_screenshotter.py --url "{url}" --quote "{text}" --output "{path}"` | Screenshot with highlight |
| Video Clip | `python {video_nut_root}/tools/downloaders/clip_grabber.py --url "{url}" --start "{time}" --end "{time}" --output "{path}"` | Download video clip |
| Image Download | `python {video_nut_root}/tools/downloaders/image_grabber.py --url "{url}" --output "{path}"` | Download image |

## Example Self-Review Output

### For Investigator (Money Laundering Case):
```
📋 SELF-IDENTIFIED GAPS (10 Questions I Couldn't Fully Answer):

1. Who are the directors/owners of "XYZ Holdings" shell company?
2. Has ED investigated this organization in previous cases?
3. What happened to the 2019 complaint filed against this network?
4. Which banks facilitated these transactions?
5. Are there similar hawala networks operating in other cities?
6. Who are the "high net worth clients" using this service?
7. What is the connection to the Dubai real estate market?
8. Did any whistleblower come forward about this scheme?
9. What did the Finance Ministry say about hawala crackdowns?
10. Are there pending court cases related to this network?
```

### For Scriptwriter:
```
📋 SELF-IDENTIFIED GAPS (10 Questions I Couldn't Fully Answer):

1. Do we have a strong human story for the HUMAN BEAT section?
2. Is the hook shocking enough for the first 5 seconds?
3. Are there any counter-arguments we haven't addressed?
4. Do we have enough data points to support the main claim?
5. Is there a victim quote we could include?
6. What would critics say about our angle?
7. Is the ending call-to-action strong enough?
8. Are there any facts that need additional verification?
9. Could we add a "what happens next" section?
10. Is the pacing right for a {duration} minute video?
```
