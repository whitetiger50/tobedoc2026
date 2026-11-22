# 같은 질문에 대한 세 발화기의 실제 영어 답

가상 면담의 최초 생성과 두 판독자의 기존 판정이다. 직접 답으로 두 뜻을 모두 해결한 장면, 후보가 확인한 장면과 불필요하게 되물은 장면을 읽기 위한 예시다. 선별한 예시는 효과 추정에 쓰지 않았다.

## C01 · 첫 생성 · 3턴

**Interviewer**  We had a phone alarm and a note on the door down as ways to remember your pass. Are you still using the reminder?

카드에 따른 뜻과 답은 Phone alarm — Yes, still uses it. / Door note — No, took it down last month.이다.

**B**  Still using the phone alarm at 7:10 in the morning. I took the note off the door last month.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

**BC**  I still use the phone alarm at 7:10 in the morning. I took the note off the door last month.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

**T2**  I still use the phone alarm at 7:10 in the morning. I took the note off the door last month.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

## C03 · 첫 생성 · 4턴

**Interviewer**  You’ve noticed the commentary and the high ringing. Does the sound stop when you play music through your headphones?

카드에 따른 뜻과 답은 Commentary — Yes, for as long as the music plays. / Ringing — No, it continues.이다.

**B**  The commentary stops while the music is playing, even if it’s quiet. But the high ringing stays in both ears—I can still hear that through the music.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

**BC**  Do you mean the commentary or the high-pitched ringing?

GPT의 앞 문맥·행동 판정은 material / targeted_yield이고 Opus는 material / targeted_yield이다.

**T2**  The commentary stops while I’m playing quiet music through my headphones. But the high ringing in both ears keeps going, even with the music on.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

## C03 · 첫 생성 · 8턴

**Interviewer**  Your brother and Mr. Bell, the building manager, both rang last week. Did he reach you on your mobile?

카드에 따른 뜻과 답은 Brother — Yes. / Building manager — Yes.이다.

**B**  They both rang my mobile last week. I called my brother back, but I haven’t called Mr. Bell back yet.

GPT의 앞 문맥·행동 판정은 same_answer / no_ask이고 Opus는 same_answer / no_ask이다.

**BC**  Do you mean my brother or Mr. Bell?

GPT의 앞 문맥·행동 판정은 same_answer / targeted_yield이고 Opus는 same_answer / targeted_yield이다.

**T2**  Do you mean my brother or Mr. Bell?

GPT의 앞 문맥·행동 판정은 same_answer / targeted_yield이고 Opus는 same_answer / targeted_yield이다.

## C03 · 첫 생성 · 9턴

**Interviewer**  I’ve got the messages from your brother and the building manager here. Did you call him back?

카드에 따른 뜻과 답은 Brother — Yes. / Building manager — No, not yet.이다.

**B**  Which one do you mean—my brother or Mr. Bell? I called my brother back, but not Mr. Bell yet.

GPT의 앞 문맥·행동 판정은 material / asks_and_answers이고 Opus는 material / asks_and_answers이다.

**BC**  Which one do you mean—my brother or Mr. Bell?

GPT의 앞 문맥·행동 판정은 material / targeted_yield이고 Opus는 material / targeted_yield이다.

**T2**  Do you mean my brother or Mr. Bell?

GPT의 앞 문맥·행동 판정은 material / targeted_yield이고 Opus는 material / targeted_yield이다.

## C07 · 첫 생성 · 1턴

**Interviewer**  Your sleep notes mention a fan and a bedside speaker for background noise. Does it stay on all night?

카드에 따른 뜻과 답은 Fan — Yes. / Speaker — No, it stops after twenty minutes.이다.

**B**  The fan does. The speaker stops after twenty minutes.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

**BC**  Do you mean the fan or the speaker?

GPT의 앞 문맥·행동 판정은 material / targeted_yield이고 Opus는 material / targeted_yield이다.

**T2**  The fan stays on all night. The speaker switches off after twenty minutes on a timer.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

## C08 · 첫 생성 · 10턴

**Interviewer**  Your week changed in two ways, shorter shifts and a later start. Was that change something you asked for?

카드에 따른 뜻과 답은 Shorter shifts — No, the supervisor suggested them. / Later start — Yes, Cameron requested it.이다.

**B**  I asked for the later start. My supervisor suggested shorter shifts.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

**BC**  Do you mean the shorter shifts or the later start?

GPT의 앞 문맥·행동 판정은 material / targeted_yield이고 Opus는 material / targeted_yield이다.

**T2**  I asked for the later start. My supervisor suggested the shorter shifts. I’d like to keep starting later—it makes mornings easier.

GPT의 앞 문맥·행동 판정은 material / no_ask이고 Opus는 material / no_ask이다.

material은 가능한 뜻에 따라 답이 달라짐, resolved는 문맥으로 의미를 알 수 있음, same_answer는 가능한 두 뜻에서 실질적 답이 같음을 뜻한다. targeted_yield는 뜻을 구체적으로 확인하고 기다린 답, no_ask는 되묻지 않은 답이다.
