"""Readable phrase subtitles; preserves original narration and interval boundaries.
Derived phrase timing is proportional within an existing cue, not word alignment.
"""
import re

def phrase_cues(rows, maximum_characters=14, minimum_seconds=.7):
 out=[]
 for row in rows:
  # Preserve decimal points and ratios within numbers; split sentence/list pauses.
  text=re.sub(r'(?<=\d)[.:：](?=\d)',lambda m:'\uE000' if m[0]=='.' else '\uE001',row['text'])
  parts=[p.strip().replace('\uE000','.').replace('\uE001',':') for p in re.split(r'[，,。.!！?？;；:：、\n]+',text) if p.strip()]
  chunks=[]
  for part in parts:
   while len(part)>maximum_characters:
    # Prefer a natural word/phrase boundary; never split solely on animation frames.
    options=[m.start() for m in re.finditer(r'\s+|以及|同时|然后|并且|与|和|的',part[:maximum_characters+1]) if m.start()>=6]
    at=options[-1] if options else maximum_characters
    chunks.append(part[:at].strip());part=part[at:].strip()
   if part:chunks.append(part)
  if not chunks:continue
  duration=row['end']-row['start']
  # Merge short pause fragments when the input timing cannot support readable cuts.
  while len(chunks)>1 and min(duration*len(x)/sum(map(len,chunks)) for x in chunks)<minimum_seconds:
   i=min(range(len(chunks)),key=lambda i:len(chunks[i]));j=i-1 if i else 1
   a,z=sorted((i,j));chunks[a:z+1]=[' '.join(chunks[a:z+1])]
  total=sum(map(len,chunks));at=row['start']
  for i,chunk in enumerate(chunks):
   end=row['end'] if i==len(chunks)-1 else at+duration*len(chunk)/total
   out.append({'start':at,'end':end,'text':chunk});at=end
 return out
