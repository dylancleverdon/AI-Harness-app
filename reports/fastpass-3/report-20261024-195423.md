# Diagnostics — fastpass 3 — 2026-10-24 19:54:23


## Run

```
script: decomp_pipeline 2026-10-25.9 (build 2026-10-18.1)
command: /Users/admin/AIHarness/scripts/decomp_pipeline.py --workdir /Users/admin/glitchdecomp/fastpass 3 --from export --to organize --headless-export --ghidra-home /Users/admin/Downloads/ghidra_12.1.4_PUBLIC --project /Users/admin/glitchpt2.gpr --ctx 8192 --parallel 50 --workers 12 --lang c --no-pseudo --repair-minutes 1 --plugin /Users/admin/Downloads/Glitch_2_1_5_Mac_Free/Glitch2.component
python: 3.15.0 on darwin
compiler: /usr/bin/clang++ (clang)
compile flags: -Wno-c++11-narrowing -arch arm64
--ctx 8192, chars per token 2.06
model: qwen2.5-coder-3b-instruct-mlx
model requests turned down this run: 0, thinking-only answers: 0
fix stage model edits: {'calls': 7, 'no_answer': 0, 'rejected': 0}
```

## What the script struggled with

```

━━━━ what the script struggled with this run ━━━━
(errors it fixed on its own are left out; [also in the last N runs] marks the ones worth changing the script for)
rates (this run last; earlier runs above it):
  run                   compile %      quarantined %             to fix        fixer tried    fixer success %     fixer per hour  recover success %      learned fixes     learned kept %            rescued  ideas adopted/tested        test pass %
  10-24 17:54               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
  10-24 18:26               100.0                0.0                  0                  -                  -                  -                  -                 96               98.1                  -                     -                0.0
  10-24 18:56               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
  10-24 19:28               100.0                0.0                  0                  1              100.0                 23                  -                 97               98.6                  -                     -                0.0
  10-24 19:54               100.0                0.0                  0                  2               50.0                 41                  -                 99               92.5                  -                     -                0.0
couldn't handle:
  fix           1 × quarantined: used type 'X' where arithmetic or pointer type is required   e.g. FUN_0013ec40
  test          1 × the rebuilt plugin didn't load: load executable   [also in the last 3 run(s)]
                    → see build/test/test_report.txt
worked around (cost time, nothing lost):
  fix         120 × Ghidra globals / library functions nothing declared (declared once in shared.h)   e.g. LAB_001806a4   [also in the last 5 run(s)]
  fix           3 × fixes that undid each other (the cycle was stopped and the model got the function)   e.g. FUN_0013ec40   [also in the last 1 run(s)]
  fix           2 × the model repeated an edit that had already failed (skipped)   e.g. FUN_0013ec40
  link         25 × functions replaced by placeholders to link   [also in the last 5 run(s)]
```

## Log of this run (pipeline.log)

```
[19:42:07] decomp_pipeline 2026-10-25.9: /Users/admin/glitchdecomp/fastpass 3 — stages export → organize
[19:42:07]   --ctx 8192: pieces up to 5303 characters, recover stage up to 11006
[19:42:07] ━━━━ Stage 1/10 · export ━━━━ getting every function's pseudocode from Ghidra (once — after that Ghidra can be closed)
[19:42:07]   using the existing ghidra_export.json (Ghidra not needed)
[19:42:16]   Ghidra lost the return value of 3492 function(s) (273 of them empty: they return what they're given): fixing their signatures and decompiling them and their callers again (headless, read-only)
[19:43:10]   signature fix: 3492 function(s) given back their return value, 10510 decompiled again with it
[19:43:17]   callgraph.json: 22076 functions with internal calls
[19:43:17]   export: 30489/30489 functions have pseudocode, 205 data types, 30489 signatures
[19:43:17] ━━━━ Stage 2/10 · privacy ━━━━ identifying information (names, web and email addresses, bundle IDs, paths, copyright lines) is replaced in Ghidra's export, before anything else sees it; what was replaced is kept in private/ on this Mac only
[19:43:19]   privacy: 1141 replacement(s) in Ghidra's export (6 names, 14 web addresses, 8 copyright lines, 1 email address, 3 user folders, 3 bundle IDs). What was replaced: private/privacy_report.txt (stays on this Mac)
[19:43:19]   privacy: 17 stand-in(s) are values the plugin uses while it runs (bundle ID, web addresses): the rebuilt plugin's Info.plist must use the same ones (listed in private/privacy_report.txt)
[19:43:19] ━━━━ Stage 3/10 · rewrite ━━━━ Ghidra's pseudocode is written out as one C file, with the program's data (no model: the code is what Ghidra decompiled)
[19:43:49]     functions with a system function's name (the system's is used): 3: sync, setbuf, objc_msgSend
[19:43:49]     Ghidra's copies of types the system headers define (the system's are used): 63, e.g. Byte, CGPoint, CGRect, CGSize, FILE, SEL
[19:43:49]     fields Ghidra named that the system's type calls something else (read at their offset): 14
[19:43:53]     pointers only the loader's fix-up list has (no reference in Ghidra): 583, fixed up too
[19:43:53]     static initializers the plugin runs when it loads (as the original does): 91
[19:43:53]     pointers in the data to addresses outside it (not fixed up): 7, listed in rewrite/data_unresolved_pointers.txt
[19:43:53]     data found by its address (not in Ghidra's label list): 496
[19:44:43]     addresses in the data written in the code as numbers ((long *)0x453400): 320, now the rebuilt data's
[19:44:57]     pieces of variables (v._0_8_): 4434
[19:44:57]     16-byte register values (as gh16): 1601
[19:44:57]     functions Ghidra said return nothing, whose callers use the result: 1352
[19:44:57]     C++/Objective-C names in definitions: 1285
[19:44:57]     C++ qualified names in code: 190
[19:44:57]     types C didn't know (declared opaque): 19
[19:44:57]     types that are also functions (as struct tags): 18
[19:44:57]     switches on a pointer (on its value): 11
[19:44:57]     NAN(x) tests (as isnan): 8
[19:44:57]     of those, returning a stand-in 0 (nothing to return in Ghidra's code): 1037, listed in rewrite/lost_returns.txt
[19:45:02]     names that are a type and also a function (the type keeps its struct tag): 12
[19:45:02]   C source from Ghidra's pseudocode: 30173 function(s), 311 library stub(s) called directly, 29 data type(s) with Ghidra's layout, the program's data (35 block(s), 2997 labelled location(s) used, 33768 pointer fix-up(s), 1 placeholder(s) for data outside the export: rewrite/data_placeholders.txt) -> pseudocode.c
[19:45:02] ━━━━ Stage 4/10 · split ━━━━ libclang splits the rewrite into shared.h + one file per function, repairs the header, then compiles every function on its own
[19:47:55] ━━━━ Stage 5/10 · fix ━━━━ functions that don't compile are repaired, callees first: quick deterministic fixes, then the model; what can't be fixed is quarantined
[19:51:48]   fix: 14 model request(s); the model was busy 11% of the stage's 3m
[19:51:48] ━━━━ Stage 6/10 · recover ━━━━ quarantined functions are rebuilt from their Ghidra pseudocode
[19:51:48] ━━━━ Stage 7/10 · link ━━━━ the whole program is compiled and linked; anything still missing gets a placeholder and is listed in link_report.txt
[19:54:03] ━━━━ Stage 8/10 · test ━━━━ the rebuilt plugin and the original (--plugin) render the same test signals in a small test host; their outputs are compared sample by sample
[19:54:09]   test: the rebuilt plugin didn't load: crashed (SIGSEGV) during: load executable
[19:54:09]   test: everything it saw is in /Users/admin/glitchdecomp/fastpass 3/build_c/test/test_report.txt
[19:54:09] ━━━━ Stage 9/10 · improve ━━━━ the code is made easier to read (names, Ghidra's helpers, casts, pointer arithmetic), worst functions first; a change is kept only if the function compiles to the same machine code, so the plugin does exactly what it did
[19:54:09]   improve: off (it's slow, and optional: the final code builds without it). Turn it on with --improve
[19:54:09] ━━━━ Stage 10/10 · organize ━━━━ the whole program is written out as one C source file, final/program.c, with its headers, its data and build.sh; final/ is only replaced once that builds
[19:54:23] ============================================================
[19:54:23] SUMMARY: 30172/30173 functions compile, 1 quarantined, 1 re-derived, link=OK
[19:54:23] Report: /Users/admin/glitchdecomp/fastpass 3/REPORT.md
[19:54:23] 
[19:54:23] ━━━━ what the script struggled with this run ━━━━
[19:54:23] (errors it fixed on its own are left out; [also in the last N runs] marks the ones worth changing the script for)
[19:54:23] rates (this run last; earlier runs above it):
[19:54:23]   run                   compile %      quarantined %             to fix        fixer tried    fixer success %     fixer per hour  recover success %      learned fixes     learned kept %            rescued  ideas adopted/tested        test pass %
[19:54:23]   10-24 17:54               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
[19:54:23]   10-24 18:26               100.0                0.0                  0                  -                  -                  -                  -                 96               98.1                  -                     -                0.0
[19:54:23]   10-24 18:56               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
[19:54:23]   10-24 19:28               100.0                0.0                  0                  1              100.0                 23                  -                 97               98.6                  -                     -                0.0
[19:54:23]   10-24 19:54               100.0                0.0                  0                  2               50.0                 41                  -                 99               92.5                  -                     -                0.0
[19:54:23] couldn't handle:
[19:54:23]   fix           1 × quarantined: used type 'X' where arithmetic or pointer type is required   e.g. FUN_0013ec40
[19:54:23]   test          1 × the rebuilt plugin didn't load: load executable   [also in the last 3 run(s)]
[19:54:23]                     → see build/test/test_report.txt
[19:54:23] worked around (cost time, nothing lost):
[19:54:23]   fix         120 × Ghidra globals / library functions nothing declared (declared once in shared.h)   e.g. LAB_001806a4   [also in the last 5 run(s)]
[19:54:23]   fix           3 × fixes that undid each other (the cycle was stopped and the model got the function)   e.g. FUN_0013ec40   [also in the last 1 run(s)]
[19:54:23]   fix           2 × the model repeated an edit that had already failed (skipped)   e.g. FUN_0013ec40
[19:54:23]   link         25 × functions replaced by placeholders to link   [also in the last 5 run(s)]
```

## Build status

```
{
 "functions": 30173,
 "compile": 30172,
 "quarantined": 1,
 "to fix": 0
}
```

## Quarantined: 1 function(s), by first error

-      1 × used type 'X' where arithmetic or pointer type is required

### Quarantined — 1 × used type 'X' where arithmetic or pointer type is required

All: FUN_0013ec40 (13ec40)

#### FUN_0013ec40 — funcs/_FUN_0013ec40.cpp, Ghidra 13ec40, 6 model attempt(s)

Compiler output:
```
/Users/admin/glitchdecomp/fastpass 3/build_c/funcs/_FUN_0013ec40.cpp:67:22: error: used type 'struct streambuf' where arithmetic or pointer type is required
   67 |     param_1[0x192] = (struct streambuf)(SUB81(uVar2, 0));
      |                      ^                 ~~~~~~~~~~~~~~~~~
1 error generated.
```
Code:
```cpp
#include "shared.h"

struct streambuf * FUN_0013ec40(struct streambuf *param_1)
{
  long *plVar1;
  undefined8 uVar2;
  uint64_t alStack_38 [8];
  struct streambuf *local_30;
  struct streambuf *local_28;

  local_30 = param_1;
  local_28 = param_1;
  plVar1 = (long *)streambuf(param_1);
  *plVar1 = (long)(GD_PTR_DAT_00424180 + 0x10);
  plVar1[9] = 0;
  plVar1[8] = 0;
  plVar1[10] = 0;
  plVar1[0xd] = 0;
  plVar1[0xc] = 0;
  plVar1[0xf] = 0;
  plVar1[0xe] = 0;
  plVar1[0x10] = 0;
  plVar1[0x12] = 0;
  plVar1[0x11] = 0;
  plVar1[0x14] = 0;
  plVar1[0x13] = 0;
  plVar1[0x16] = 0;
  plVar1[0x15] = 0;
  plVar1[0x18] = 0;
  plVar1[0x17] = 0;
  plVar1[0x1a] = 0;
  plVar1[0x19] = 0;
  plVar1[0x1c] = 0;
  plVar1[0x1b] = 0;
  plVar1[0x1e] = 0;
  plVar1[0x1d] = 0;
  plVar1[0x20] = 0;
  plVar1[0x1f] = 0;
  plVar1[0x22] = 0;
  plVar1[0x21] = 0;
  plVar1[0x24] = 0;
  plVar1[0x23] = 0;
  plVar1[0x26] = 0;
  plVar1[0x25] = 0;
  plVar1[0x28] = 0;
  plVar1[0x27] = 0;
  plVar1[0x2a] = 0;
  plVar1[0x29] = 0;
  plVar1[0x2c] = 0;
  plVar1[0x2b] = 0;
  plVar1[0x2e] = 0;
  plVar1[0x2d] = 0;
  plVar1[0x30] = 0;
  plVar1[0x2f] = 0;
  plVar1[0x31] = 0;
  *(undefined2 *)(plVar1 + 0x32) = 0;
  *(undefined1 *)((long)plVar1 + 0x192) = 0;
  FUN_0013ed94(alStack_38,(long)plVar1);
  uVar2 = FUN_0013ed68((id *)alStack_38);
  locale_385f00(alStack_38);
  if ((int)uVar2 != 0) {
    FUN_0013ed94(alStack_38,(long)param_1);
    uVar2 = FUN_0013e2dc((id *)alStack_38);
    *(undefined8 *)(param_1 + 0x80) = uVar2;
    locale_385f00(alStack_38);
    uVar2 = FUN_0013e304(*(long **)(param_1 + 0x80));
    param_1[0x192] = SUB81(uVar2,0);
  }
  (**(code **)(*(long *)param_1 + 0x18))(param_1,0,0x1000);
  return local_28;
}
```
Notes:
- 10-22 13:33 [compile] used type 'struct streambuf' where arithmetic or pointer type is required — fixed with a learned rule.
- 10-22 13:33 [compile] assigning to 'struct streambuf' from incompatible type 'uint64_t' (aka 'unsigned long long') — fixed by a candidate fix: a value converted to the type it's assigned to — compiles now.
- 10-24 19:51 [compile] the model suggested an edit that already failed — skipped.
- 10-24 19:51 [compile] the no-model fixes went round in circles — stopped; the model gets the best version they reached.
- 10-24 19:51 [compile] assigning to 'struct streambuf' from incompatible type 'uint8_t' (aka 'unsigned char') — plan: Change `param_1[0x192] = SUB81(uVar2,0);` to `param_1[0x192] = (struct streambuf)SUB81(uVar2,0);` — still fails: used type 'struct streambuf' where arithmetic or pointer type is required
- 10-24 19:51 [compile] assigning to 'struct streambuf' from incompatible type 'uint8_t' (aka 'unsigned char') — plan: Change `param_1[0x192] = SUB81(uVar2,0);` to `param_1[0x192] = (struct streambuf)SUB81(uVar2,0);` — still fails: used type 'struct streambuf' where arithmetic or pointer type is required
- 10-24 19:51 [compile] used type 'struct streambuf' where arithmetic or pointer type is required — plan: Change `param_1[0x192] = SUB81(uVar2,0);` to `param_1[0x192] = (struct streambuf)SUB81(uVar2,0);` — still fails: used type 'struct streambuf' where arithmetic or pointer type is required
- 10-24 19:51 [compile] that edit didn't help — undone.
- 10-24 19:51 [compile] the no-model fixes went round in circles — stopped; the model gets the best version they reached.
- 10-24 19:51 [compile] the model suggested an edit that already failed — skipped.
- 10-24 19:51 [compile] the no-model fixes went round in circles — stopped; the model gets the best version they reached.
- 10-24 19:51 [compile] assigning to 'struct streambuf' from incompatible type 'uint8_t' (aka 'unsigned char') — plan: Change `param_1[0x192] = SUB81(uVar2,0);` to `param_1[0x192] = (struct streambuf)SUB81(uVar2, 0);` — still fails: used type 'struct streambuf' where arithmetic or pointer type is required
Ghidra's pseudocode:
```c
streambuf * FUN_0013ec40(streambuf *param_1)

{
  long *plVar1;
  undefined8 uVar2;
  locale alStack_38 [8];
  streambuf *local_30;
  streambuf *local_28;
  
  local_30 = param_1;
  local_28 = param_1;
  plVar1 = (long *)std::streambuf::streambuf(param_1);
  *plVar1 = (long)(PTR_DAT_00424180 + 0x10);
  plVar1[9] = 0;
  plVar1[8] = 0;
  plVar1[10] = 0;
  plVar1[0xd] = 0;
  plVar1[0xc] = 0;
  plVar1[0xf] = 0;
  plVar1[0xe] = 0;
  plVar1[0x10] = 0;
  plVar1[0x12] = 0;
  plVar1[0x11] = 0;
  plVar1[0x14] = 0;
  plVar1[0x13] = 0;
  plVar1[0x16] = 0;
  plVar1[0x15] = 0;
  plVar1[0x18] = 0;
  plVar1[0x17] = 0;
  plVar1[0x1a] = 0;
  plVar1[0x19] = 0;
  plVar1[0x1c] = 0;
  plVar1[0x1b] = 0;
  plVar1[0x1e] = 0;
  plVar1[0x1d] = 0;
  plVar1[0x20] = 0;
  plVar1[0x1f] = 0;
  plVar1[0x22] = 0;
  plVar1[0x21] = 0;
  plVar1[0x24] = 0;
  plVar1[0x23] = 0;
  plVar1[0x26] = 0;
  plVar1[0x25] = 0;
  plVar1[0x28] = 0;
  plVar1[0x27] = 0;
  plVar1[0x2a] = 0;
  plVar1[0x29] = 0;
  plVar1[0x2c] = 0;
  plVar1[0x2b] = 0;
  plVar1[0x2e] = 0;
  plVar1[0x2d] = 0;
  plVar1[0x30] = 0;
  plVar1[0x2f] = 0;
  plVar1[0x31] = 0;
  *(undefined2 *)(plVar1 + 0x32) = 0;
  *(undefined1 *)((long)plVar1 + 0x192) = 0;
  FUN_0013ed94(alStack_38,(long)plVar1);
  uVar2 = FUN_0013ed68((id *)alStack_38);
  std::locale::~locale(alStack_38);
  if ((int)uVar2 != 0) {
    FUN_0013ed94(alStack_38,(long)param_1);
    uVar2 = FUN_0013e2dc((id *)alStack_38);
    *(undefined8 *)(param_1 + 0x80) = uVar2;
    std::locale::~locale(alStack_38);
    uVar2 = FUN_0013e304(*(long **)(param_1 + 0x80));
    param_1[0x192] = SUB81(uVar2,0);
  }
  (**(code **)(*(long *)param_1 + 0x18))(param_1,0,0x1000);
  return local_28;
}
```

## build/split_report.txt

```
unresolved struct fields (unknown type, left as comments): 0
```

## build/libclang_parse_errors.txt

```
_parse_monolith.cpp:220: static assertion failed due to requirement 'sizeof(struct section) == 80': Ghidra's size of section
_parse_monolith.cpp:236: static assertion failed due to requirement 'sizeof(struct segment_command) == 72': Ghidra's size of segment_command
```

## build/header_repair_report.txt

```
disabled proto out_of_range   <- redefinition of 'out_of_range' as different kind of symbol
disabled proto length_error   <- redefinition of 'length_error' as different kind of symbol
```

## build/fix_report.txt

```
why 1 function(s) are quarantined (first compile error, grouped):

     1  assigning to 'X' from incompatible type 'X' (aka 'X')
        e.g. FUN_0013ec40
```

## build/link_report.txt

```
stubbed DAT_0042e5a8 (never defined)
stubbed FUN_0013ec40 (quarantined)
stubbed FUN_00230160 (never defined)
stubbed FUN_00315c (never defined)
stubbed FUN_004536f8 (never defined)
stubbed FUN_00453790 (never defined)
stubbed FUN_004537b8 (never defined)
stubbed FUN_00453810 (never defined)
stubbed FUN_004538a8 (never defined)
stubbed FUN_004538c0 (never defined)
stubbed FUN_00453900 (never defined)
stubbed FUN_00453d30 (never defined)
stubbed FUN_00453d70 (never defined)
stubbed FUN_00453e28 (never defined)
stubbed FUN_00454130 (never defined)
stubbed FUN_00454148 (never defined)
stubbed FUN_00454268 (never defined)
stubbed FUN_008716a0 (never defined)
stubbed _init (not in the program or the system libraries: a placeholder)
_logf: forwarded to the library's logf
_next_prime: forwarded to the library's _ZNSt3__112__next_primeEm
stubbed _throw_length_error (not in the program or the system libraries: a placeholder)
addButtonWithTitle_: an Objective-C message (addButtonWithTitle:), sent for real
addObserver_selector_name_object_: an Objective-C message (addObserver:selector:name:object:), sent for real
applicationShouldTerminate_: an Objective-C message (applicationShouldTerminate:), sent for real
arrayWithCapacity_: an Objective-C message (arrayWithCapacity:), sent for real
arrayWithObject_: an Objective-C message (arrayWithObject:), sent for real
arrayWithObjects_: an Objective-C message (arrayWithObjects:), sent for real
arrayWithObjects_count_: an Objective-C message (arrayWithObjects:count:), sent for real
buildMenuGroupEntries_entry_: an Objective-C message (buildMenuGroupEntries:entry:), sent for real
bundleWithPath_: an Objective-C message (bundleWithPath:), sent for real
characterAtIndex_: an Objective-C message (characterAtIndex:), sent for real
constraintWithItem_attribute_relatedBy_toItem_attribute_multiplier_constant_: an Objective-C message (constraintWithItem:attribute:relatedBy:toItem:attribute:multiplier:constant:), sent for real
convertRectFromBacking_: an Objective-C message (convertRectFromBacking:), sent for real
convertRectToBacking_: an Objective-C message (convertRectToBacking:), sent for real
createLayerTextureWithSize_: an Objective-C message (createLayerTextureWithSize:), sent for real
defaultWritingDirectionForLanguage_: an Objective-C message (defaultWritingDirectionForLanguage:), sent for real
deminiaturize_: an Objective-C message (deminiaturize:), sent for real
dictionaryWithContentsOfFile_: an Objective-C message (dictionaryWithContentsOfFile:), sent for real
drawRect_: an Objective-C message (drawRect:), sent for real
fileURLWithPath_: an Objective-C message (fileURLWithPath:), sent for real
getReturnValue_: an Objective-C message (getReturnValue:), sent for real
graphicsContextWithWindow_: an Objective-C message (graphicsContextWithWindow:), sent for real
initWithContentRect_styleMask_backing_defer_: an Objective-C message (initWithContentRect:styleMask:backing:defer:), sent for real
initWithContentsOfFile_: an Objective-C message (initWithContentsOfFile:), sent for real
initWithFrame_: an Objective-C message (initWithFrame:), sent for real
initWithFrame_frame_: an Objective-C message (initWithFrame:frame:), sent for real
initWithImage_hotSpot_: an Objective-C message (initWithImage:hotSpot:), sent for real
initWithString_: an Objective-C message (initWithString:), sent for real
initWithTitle_: an Objective-C message (initWithTitle:), sent for real
initWithTitle_action_keyEquivalent_: an Objective-C message (initWithTitle:action:keyEquivalent:), sent for real
insertText_: an Objective-C message (insertText:), sent for real
invocationWithMethodSignature_: an Objective-C message (invocationWithMethodSignature:), sent for real
invokeWithTarget_: an Objective-C message (invokeWithTarget:), sent for real
keyEquivalentFromMenuEntry_: an Objective-C message (keyEquivalentFromMenuEntry:), sent for real
markedTextAbandoned_: an Objective-C message (markedTextAbandoned:), sent for real
miniaturize_: an Objective-C message (miniaturize:), sent for real
modflagsFromMenuEntry_: an Objective-C message (modflagsFromMenuEntry:), sent for real
objectAtIndex_: an Objective-C message (objectAtIndex:), sent for real
objectForKey_: an Objective-C message (objectForKey:), sent for real
operator_delete: forwarded to the library's _ZdlPv
operator_delete__: forwarded to the library's _ZdaPv
operator_new__: forwarded to the library's _Znam
otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_: an Objective-C message (otherEventWithType:location:modifierFlags:timestamp:windowNumber:context:subtype:data1:data2:), sent for real
performClose_: an Objective-C message (performClose:), sent for real
performFileOperation_source_destination_files_tag_: an Objective-C message (performFileOperation:source:destination:files:tag:), sent for real
removeObserver_: an Objective-C message (removeObserver:), sent for real
respondsToSelector_: an Objective-C message (respondsToSelector:), sent for real
scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_: an Objective-C message (scheduledTimerWithTimeInterval:target:selector:userInfo:repeats:), sent for real
sendEvent_: an Objective-C message (sendEvent:), sent for real
setAllowGPUOptimizedContents_: an Objective-C message (setAllowGPUOptimizedContents:), sent for real
setAllowGettingClosed_: an Objective-C message (setAllowGettingClosed:), sent for real
setAutoForwardKeyEvents_: an Objective-C message (setAutoForwardKeyEvents:), sent for real
setCanChooseFiles_: an Objective-C message (setCanChooseFiles:), sent for real
setCanCreateDirectories_: an Objective-C message (setCanCreateDirectories:), sent for real
setCommandQueue_: an Objective-C message (setCommandQueue:), sent for real
setContentSizeConstraints_: an Objective-C message (setContentSizeConstraints:), sent for real
setContentSize_: an Objective-C message (setContentSize:), sent for real
setCppParent_: an Objective-C message (setCppParent:), sent for real
setCppWindow_: an Objective-C message (setCppWindow:), sent for real
setCpuCacheMode_: an Objective-C message (setCpuCacheMode:), sent for real
setCurrentInterpretKeyEventsKey_: an Objective-C message (setCurrentInterpretKeyEventsKey:), sent for real
setFrame_display_: an Objective-C message (setFrame:display:), sent for real
setMenuBarVisible_: an Objective-C message (setMenuBarVisible:), sent for real
setPluginShell_: an Objective-C message (setPluginShell:), sent for real
setSelector_: an Objective-C message (setSelector:), sent for real
setStyleMask_: an Objective-C message (setStyleMask:), sent for real
setSubmenu_: an Objective-C message (setSubmenu:), sent for real
setTexture_: an Objective-C message (setTexture:), sent for real
setTitle_: an Objective-C message (setTitle:), sent for real
setUsage_: an Objective-C message (setUsage:), sent for real
stringWithCharacters_length_: an Objective-C message (stringWithCharacters:length:), sent for real
stringWithFormat_: an Objective-C message (stringWithFormat:), sent for real
stringWithUTF8String_: an Objective-C message (stringWithUTF8String:), sent for real
texture2DDescriptorWithPixelFormat_width_height_mipmapped_: an Objective-C message (texture2DDescriptorWithPixelFormat:width:height:mipmapped:), sent for real
updateLayerInRect_: an Objective-C message (updateLayerInRect:), sent for real
validateMenuItem_: an Objective-C message (validateMenuItem:), sent for real
viewWillMoveToSuperview_: an Objective-C message (viewWillMoveToSuperview:), sent for real
zoom_: an Objective-C message (zoom:), sent for real
```

## build/link_errors.txt

```
ld: warning: ignoring duplicate libraries: '-lc++'
Undefined symbols for architecture arm64:
  "_length_error", referenced from:
      _gd_targets in ghidra_data.o
  "_out_of_range", referenced from:
      _gd_targets in ghidra_data.o
ld: symbol(s) not found for architecture arm64
clang++: error: linker command failed with exit code 1 (use -v to see invocation)
```

## build/learned_fixes.txt

```
Fixes this project learned from the model's edits (@1, @2 ... stand for any
name). Proven ones are applied without the model; candidates are tried on
every function with the same error and kept only where they work.

== proven: 99
[338 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(@4);
  → @1 = @3(@4);
[236 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1 = @2((@3)@4);
  → @1 = @2((@3)@4, 1);
[208 worked, 53 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = @2(
  → unsigned char @1[16] = {0};@2(
[203 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2[16];
  → uint64_t @2;
[175 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 1;
  → *(unsigned char*)&@1 = (unsigned char)1;
[170 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@1.@3, 1);
  → @1 = @2(*(unsigned char*)&@1, 1);
[112 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → unsigned char @1[16] = {0};@2(@3);
[99 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    (@1);
  → (@1, 1);
[87 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → *(unsigned char*)&@1 = @2(@3, @4);
[82 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16];
[73 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2.@3;
  → @1 = @2[8];
[70 worked, 12 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1*@2;
  → uint64_t @2;
[69 worked, 6 didn't] integer constant expression must have integer type, not 'X'
    case"" :
  → case 0 :
[67 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    )@1);
  → )@1, 1);
[64 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (void*)@2(
  → @1 = @2(
[44 worked, 12 didn't] initializing 'X' with an expression of incompatible type 'X' (part of a line)
    @1 = @2(
  → @1 = (unsigned long long)@2(
[43 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2.@3;
  → *(unsigned char*)&@1 = *(unsigned char*)&@2;
[35 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2();
  → (void)@1 = @2();
[31 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(@2);
  → @1(@2, 1);
[30 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3;
  → @1[8] = @3;
[29 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 0;
  → @1[8] = 0;
[27 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1, (
  → 0], (
[25 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → unsigned char @1[16];@2(@3, @4);
[25 worked, 2 didn't] too few arguments to function call, expected N, have N (part of a line)
    @1();
  → @1(1);
[25 worked, 6 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2();
  → uint64_t @1 = @2();
[21 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5);
  → unsigned char @1[16] = {0};@2(@3, @4, @5);
[20 worked, 0 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1(@2
  → ((uint64_t(*)())@1)(@2
[20 worked, 1 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    @1 = @2((
  → @1 = ((uint64_t(*)())@2)((
[19 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2((long)@3);
  → uintptr_t @1 = @2((long)@3);
[18 worked, 8 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1[0] = @2(
  → unsigned char @1[1] = {0};@2(
[16 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (long)@2(@3, @4);
  → long @1 = @2(@3, @4);
[14 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@1.@3, @4);
  → @1 = @2(*(unsigned int*)&@1, @4);
[14 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16] = {0};@2();
[12 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned char @1[16] = {0};@2(@3, @4, @5, @6, @7, @8, @9);
[12 worked, 3 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = (*
  → unsigned char @1[16] = {0};(*
[11 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = 0;
  → @1[0] = 0;
[11 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\x01" :
  → case 1 :
[11 worked, 0 didn't] too few arguments to function call, single argument 'X' was not specified (part of a line)
    @1()
  → ((uint64_t(*)())@1)()
[10 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    int @1 = (int)@2(
  → long @1 = @2(
[10 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(@2[0]);
  → @1(@2[0], 1);
[9 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    , @1.@2, @1.@3, @4.@2, @4.@3, @5.@2,
  → , @1[0], @1[8], @4[0], @4[8], @5[0], @5[8]);
[8 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@3.@4, @3.@5, @6, @7);
  → @1 = @2(@3, @6, @7);
[8 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    long)@1[0x68]+3
  → long)(@1+0x68)+3
[8 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    *(@1(*)[16])(@2+(long)@3) = @4[0];
  → memcpy(&(*(@1(*)[16])(@2+(long)@3)), &(@4[0]), sizeof(*(@1(*)[16])(@2+(long)@3))<sizeof(@4[0]) ? sizeof(*(@1(*)[16])(@2+(long)@3)) : sizeof(@4[0]));
[7 worked, 0 didn't] variable has incomplete type 'X'
    void std:: @1:: @1(@1*this)
  → void @1(@1*this)
[7 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = @2(@1[0].@3, 1);
  → @1[0] = @2(@1[0], 1);
[7 worked, 0 didn't] redefinition of 'X' (part of a line)
    @1 @2 = {@3
  → @2 = (@1){@3
[6 worked, 0 didn't] expected 'X' after expression
    std:: @1:: @2(@3);
  → return std:: @1:: @2(@3);
[6 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2((@3*)(@4+0x168));
  → void*@1 = @2((@3*)(@4+0x168));
[6 worked, 0 didn't] variable has incomplete type 'X' (part of a line)
    void std:: @1:: @2(
  → void @2(
[6 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0].@2 = 0x640001;
  → @1[0] = 0x640001;
[6 worked, 0 didn't] called object type 'X' (aka 'X') is not a function or function pointer (part of a line)
    ((@1)(
  → ((int)(
[6 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    )@1[0x68]+2)
  → )@1+0x68*2)
[6 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (long)@2[7]+0x20;
  → @1 = (long)(@2+7)+0x20;
[6 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\b" :
  → case'\b' :
[6 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    *@1 =
  → *(uint64_t*)@1 =
[5 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@1.@3, (int)@1+1);
  → @1 = @2(*(unsigned int*)&@1, (int)@1+1);
[5 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (int)@1[0]+1;
  → @1[0] = (int)@1[0]+1;
[5 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2((@3*)(@4+0x88));
  → void*@1 = @2((@3*)(@4+0x88));
[5 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0xd0);
  → long @1 = @3(0xd0);
[5 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    = @1.@2;
  → = @1[0];
[5 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    (1);
  → (1, 0);
[5 worked, 0 didn't] used type 'X' where arithmetic or pointer type is required
    @1 = (struct @2)@3(*(long**)(@4+0x80));
  → @1 = @3(*(long**)(@4+0x80));
[5 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (@2*)@3[1];
  → @1 = *(@2**)(@3+1);
[5 worked, 0 didn't] indirection requires pointer operand ('X' invalid) (part of a line)
    *@1(
  → @1(
[5 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    (*@1+
  → (*(uint64_t*)@1+
[5 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    *(@1+
  → *(uint64_t*)(@1+
[5 worked, 1 didn't] member reference base type 'X' is not a structure or union (part of a line)
    @1.@2 = @3
  → @1[1] = @3
[4 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3();
  → @1 = @3();
[4 worked, 0 didn't] expected 'X' after expression
    @1 = (long*)std:: @2:: @2(@3, @4);
  → @1 = (long*)new std:: @2(@3, @4);
[4 worked, 0 didn't] expected 'X' after return statement
    return std:: @1:: @2(@3);
  → return;
[4 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = 0x3f800000;
  → @1[0] = 0x3f800000;
[4 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (long*)@2(0xd0);
  → @1 = @2(0xd0);
[4 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long @1 = @2(0xd0);
  → unsigned long @1 = @2(0xd0);
[4 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    *@1 = @2.@3;
  → *@1 = @2[0];
[4 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    (@1);
  → (@1, 0);
[4 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\f" :
  → case 0x0C :
[4 worked, 1 didn't] used type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (struct @2)@3(
  → @1 = @3(
[3 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3(@4);
  → *(unsigned char*)&@1 = (unsigned char)@3(@4);
[3 worked, 0 didn't] variable has incomplete type 'X'
    void std:: @1:: @2:: @2(@2*this, @1*@3)
  → void @2(@2*this, @1*@3)
[3 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    @1(@2.@3);
  → @1(*(unsigned char*)&@2);
[3 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = @2(@3.@4*(double)(@5+-1));
  → @1[0] = @2(@3*(double)(@5+-1));
[3 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, @4+1);
  → unsigned long long @1 = @2(@3, @4+1);
[3 worked, 0 didn't] redefinition of 'X'
    @1 @2 = @3(0x14);
  → unsigned long @2 = @3(0x14);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1[0] = @2(@3, @4, @5, @6, @7, (long)@8[0], @9)
  → @1[0] = @2((unsigned char*)@3, @4, @5, @6, @7, (long)@8[0], @9);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = @2(@3(@4, @5, @6, @7, @8, *(int*)(@9+400)));
  → unsigned char @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8, *(int*)(@9+400)));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X'
    unsigned char @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8, *(int*)(@9+400)));
  → unsigned char @1 = @2(@3(@4, @5, @6, @7, @8, *(int*)(@9+400)));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = @2(@3, @4, @5, @6, (long)@7, (@8*)@9);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, (long)@7, (@8*)@9);
[3 worked, 0 didn't] called object type 'X' (aka 'X') is not a function or function pointer
    @1 = @2(@3((@4)((@5)@6>>0x28), @7), @8);
  → @1 = @2(@3((int)((@5)@6>>0x28), @7), @8);
[3 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    long)@1[7]+0x20
  → long)(@1+7)+0x20
[3 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@3, (long*)&@4.@5);
  → @1 = @2(@3, (long*)@3[0x6c]+3);
[3 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(*(@2*)(@3+0x20));
  → ((uint64_t(*)())@1)(*(@2*)(@3+0x20));
[3 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[1
  → ((uint64_t*)(uintptr_t)(@1))[1
[3 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1;
  → uint64_t @1 = 0;
[3 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1(@2, @3, @4, @5, @6, (long)@7[0], @8)
  → @1((unsigned char*)@2, @3, @4, @5, @6, (long)@7[0], @8);
[3 worked, 1 didn't] too few arguments to function call, expected N, have N (part of a line)
    (0x3ff0000000000000);
  → (0x3ff0000000000000, 0);
[3 worked, 1 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = *(long*)((long)&@2.@3+@4);
  → @1 = *(long*)((long)@4[0x6a]+@4);
[3 worked, 1 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[2
  → ((uint64_t*)(uintptr_t)(@1))[2
[3 worked, 1 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    @1 = @2(@3
  → @1 = ((uint64_t(*)())@2)(@3

== candidate: 489
[85 worked, 206 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X') (part of a line)
    @1 @2[
  → uint64_t @2[
[57 worked, 54 didn't] redefinition of 'X'
    @1 @2;
  → @1*@2;
[46 worked, 42 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2;
  → uint64_t @2;
[24 worked, 21 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    @1 = (*@2)();
  → @1 = @2();
[24 worked, 22 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    int @1;
  → uint64_t @1;
[16 worked, 15 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (@2*)@3(
  → @1 = @3(
[13 worked, 13 didn't] redefinition of 'X'
    @1 @2;
  → unsigned long*@2;
[11 worked, 9 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long @1;
  → uint64_t @1;
[11 worked, 11 didn't] too few arguments to function call, expected N, have N
    @1 = (float)@2();
  → float @1 = (float)@2(1);
[8 worked, 10 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2;
  → uint64_t @2 = 0;
[7 worked, 8 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    double @1;
  → uint64_t @1;
[6 worked, 4 didn't] operand of type 'X' where arithmetic or pointer type is required
    return(uint64_t)@1(&@2, &@3);
  → return @1(@2, @3);
[6 worked, 4 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    return(uint64_t)@1(&@2, &@3)
  → return @1(@2, @3)
[6 worked, 5 didn't] redefinition of 'X' (part of a line)
    @1 @2 =
  → @1*@2 =
[6 worked, 5 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long*@1;
  → uint64_t @1;
[5 worked, 4 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1[0] = @2(
  → unsigned char @1[16] = {0};@2(
[5 worked, 5 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    int @1;
  → uint64_t @1 = 0;
[5 worked, 5 didn't] redefinition of 'X'
    uint64_t @1;
  → unsigned long @1[16];
[5 worked, 7 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, @4, @5);
  → uint64_t @1 = @2(@3, @4, @5);
[4 worked, 3 didn't] redefinition of 'X'
    @1 @2;
  → @1*@2 = 0;
[4 worked, 3 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long*@1;
  → uint64_t*@1;
[4 worked, 3 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    unsigned long*@1
  → uint64_t*@1
[4 worked, 3 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = @2(
  → unsigned char @1[12] = {0};@2(
[4 worked, 4 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    @1 @2;
  → uint64_t @2 = 0;
[4 worked, 4 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3);
  → uint64_t @1 = @2(@3);
[3 worked, 2 didn't] redefinition of 'X'
    @1 @2 = @3(@4, @5);
  → @1*@2 = @3(@4, @5);
[3 worked, 2 didn't] redefinition of 'X' (part of a line)
    @1 @2 =
  → unsigned long @2 =
[3 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1 = @2(@3(@4,
  → unsigned char @1 = @2(@3((unsigned char*)@4,
[3 worked, 2 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    long)&@1.@2+@3
  → long)@3[0x6a]+@3
[3 worked, 2 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1, @2(@3, 0, 8), @2(@3, 8, 8), @4);
  → @1, (const char*)@2(@3, 0, 8), @2(@3, 8, 8));
[3 worked, 3 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    double @1;
  → uint64_t @1 = 0;
[3 worked, 3 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    double @1;
  → uint64_t @1[16];
[3 worked, 3 didn't] too many arguments to function call, expected N, have N
    @1(@2, @3(@4, 0, 8), @3(@4, 8, 8), @5);
  → @1(@2, (const char*)@3(@4, 0, 8), @3(@4, 8, 8));
[3 worked, 4 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, "");
  → uint64_t @1 = @2(@3, "");
[3 worked, 4 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3);
  → uint64_t @1[16] = {0};@2(@3);
[3 worked, 4 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1*@2;
  → uint64_t @2 = 0;
[2 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2(@3);
  → @1 = (int)@2(@3);
[2 worked, 0 didn't] must use 'X' tag to refer to type 'X'
    @1 @2;
  → struct @1 @2;
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → char @1[16];
[2 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(*@4, @5);
  → @1 = @3(*@4, @5);
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 0;
  → @1[2] = 0;
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4+1);
  → unsigned char @1[16];@2(@3, @4+1);
[2 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3();
  → @1 = @3();
[2 worked, 0 didn't] expected 'X' after expression
    std:: @1:: @2();
  → return std:: @1:: @2();
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5);
  → unsigned char @1[16];@2(@3, @4, @5);
[2 worked, 0 didn't] expression is not assignable
    (void)@1 = @2();
  → (void)@2();
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2((long)@3);
  → unsigned char @1[16];
[2 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    , @1.@2, @1.@3, @4
  → , @1, @4
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3.@4;
  → @1[0] = @3[4];
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3<<0x20;
  → *(unsigned char*)&@1 = (unsigned char)(@3<<0x20);
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2[16];@3(@4, @5, @6);
  → uint64_t @2[16];@3(@4, @5, @6);
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = (int*)@2((long*)&@3, @4.@5);
  → @1 = (int*)@2((long*)&@3, @4[0]);
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(&@3, &@4);
  → unsigned char @1[16];@2(&@3, &@4);
[2 worked, 0 didn't] member reference base type 'X' is not a structure or union
    for(@1[0].@2 = 1;@3 = (int)@1[0], @4 = @5(), @3<(int)@4;
  → for(@1[0] = 1;@3 = (int)@1[0], @4 = @5(), @3<(@4);
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0] = (@2*)@3(@1[0].@4, (int)@1[0]+1);
  → @1[0] = (@2*)@3(@1[0], (int)@1[0]+1);
[2 worked, 0 didn't] no member named 'X' in 'X'
    @1(@2, 0, 8, @2.@3&0xffffffffffffff00);
  → @1(@2, 0, 8, @3&0xffffffffffffff00);
[2 worked, 0 didn't] no member named 'X' in 'X' (part of a line)
    8, @1.@2&
  → 8, @2&
[2 worked, 0 didn't] redefinition of 'X'
    @1 @2 = @3(@4, @5, @6);
  → @1*@2 = @3(@4, @5, @6);
[2 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (int)@3;
  → @1[0] = @3;
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, @7, 5);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, 5);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, 1, @7, @8, @9, @10, 1)
  → @1((unsigned char*)@2, @3, @4, @5, @6, 1, @7, @8, @9, @10, 1);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, @7, @8, @9, @10,
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9, @10,
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = @2(@3, @4, @5, @6, @7, &@8);
  → ```@1 = @2((unsigned char*)@3, @4, @5, @6, @7, &@8);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1 = @2(@3,
  → ```@1 = @2((unsigned char*)@3,
[2 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    @1 = (@2*)*@3;
  → @1 = *(@2**)@3;
[2 worked, 0 didn't] redefinition of 'X'
    uint64_t @1;
  → uint64_t @1[1];
[2 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    ;*@1!
  → ;*(uint64_t*)@1!
[2 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    for(@1 = @2;*(uint64_t*)@1! = 0;@1 = (long*)*@1){
  → for(@1 = @2;*(uint64_t*)@1! = 0;@1 = (long*)*(uint64_t*)@1){
[2 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    )*@1)
  → )*(uint64_t*)@1)
[2 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (float)powf();
  → @1 = (float)((uint64_t(*)())powf)();
[2 worked, 0 didn't] too few arguments to function call, single argument 'X' was not specified
    @1();
  → ((uint64_t(*)())@1)();
[2 worked, 0 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1 = @2(@3
  → @1 = ((uint64_t(*)())@2)(@3
[2 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (long*)@2(0x3ff0000000000000);
  → @1 = (long*)((uint64_t(*)())@2)(0x3ff0000000000000);
[2 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    *)@1(0x3ff0000000000000
  → *)((uint64_t(*)())@1)(0x3ff0000000000000
[2 worked, 0 didn't] used type 'X' (aka 'X') where arithmetic or pointer type is required (part of a line)
    ), @1 = = (@2[4])@3(
  → ), @3(@1, 0, 4) = = @3(
[2 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    if((@1)&& (@2 = @3(@4), @2 = = 0)){
  → if((@1)&& (@2 = ((uint64_t(*)())@3)(@4), @2 = = 0)){
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → @1[16] = {0};@2(@3);
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = @2(
  → @1[16] = {0};@2(
[2 worked, 1 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = @2((long)@3);
  → @1 = @2(@3);
[2 worked, 1 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1((long)@2)
  → @1(@2)
[2 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, @7, (long*)@8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, (long*)@8);
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3);
  → unsigned char @1[16] = {0};@2(@3);
[2 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    for(@1 = (@2*)*@3;@3 = @4, @1! = @5;
  → for(@1 = *(@2**)@3;@3 = @4, @1! = @5;
[2 worked, 1 didn't] too few arguments to function call, expected N, have N
    @1 = (long*)@2(0x3ff0000000000000);
  → @1 = (long*)@2(0x3ff0000000000000, 0);
[2 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    void*@1;
  → uint64_t*@1;
[2 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    void*@1
  → uint64_t*@1
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16] = @2();
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = @2
  → unsigned char @1[16] = @2
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → unsigned char @1[12] = {0};@2(@3);
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1[0] = @2(
  → unsigned char @1[8] = {0};@2(
[2 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    (**(@1**)(*@2+8))();
  → if(@2! = NULL){(**(@1**)(@2+8))();}
[2 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    for(@1 = @2;*@1! = 0;@1 = (long*)*@1){
  → for(@1 = @2;*(uint64_t*)@1! = 0;@1 = (long*)*@1){
[2 worked, 1 didn't] used type 'X' (aka 'X') where arithmetic or pointer type is required
    (@1(@2, 3, @3), @3 = = (@4[4])@5(@6, 4, 4))){
  → (@1(@2, 3, @3), @5(@3, 0, 4) = = @5(@6, 4, 4))){
[2 worked, 2 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long*@1;
  → uint64_t @1 = 0;
[2 worked, 2 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    (**(@1**)(*@2+0x18))(@2, @3, @4);
  → if(@2! = NULL){(**(@1**)(*@2+0x18))(@2, @3, @4);}
[2 worked, 2 didn't] too many arguments to function call, expected N, have N
    @1(@2, @3(@4, 0, 8), @3(@4, 8, 8), @5);
  → @1(@2, @3(@4, 0, 8), @3(@4, 8, 8));
[2 worked, 3 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3);
  → uint64_t @1[1] = {@2(@3)};
[2 worked, 3 didn't] too many arguments to function call, expected N, have N (part of a line)
    8), @1);
  → 8));
[2 worked, 4 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, @4, @5, @6, @7, @8, @9);
  → uint64_t @1 = @2(@3, @4, @5, @6, @7, @8, @9);
[2 worked, 4 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2;
  → uint64_t @2[12];
[2 worked, 4 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1*@2;
  → uint64_t @2[12];
[2 worked, 5 didn't] assigning to 'X' from incompatible type 'X' (aka 'X') (part of a line)
    @1 = @2(
  → uint64_t @1 = (uint64_t)@2(
[2 worked, 6 didn't] invalid operands to binary expression ('X' (aka 'X') and 'X' (aka 'X'))
    @1*@2;
  → uint64_t @2;
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(@4);
  → @2*@1 = @3(@4);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x425378);
  → @1 = (void*)@2(0x425378);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → @1 = (unsigned char[16])@2();
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x42c348);
  → @1 = (void*)@2(0x42c348);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x444ba0);
  → @1 = (void*)@2(0x444ba0);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x443540);
  → @1 = (void*)@2(0x443540);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3;
  → *(unsigned char*)&@1 = (unsigned char)@3;
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, 0);
  → @1 = (unsigned char[16])@2(@3, @4, 0);
[1 worked, 0 didn't] expected 'X' after top level declarator
    @1 @2[16]@3(@4*@5, @6*@7);
  → @1 @2[16];@3(@4*@5, @6*@7);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(&@3, &@4);
  → *(unsigned char*)&@1 = (unsigned char)@2(&@3, &@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x43df20);
  → @1 = @3(0x43df20);
[1 worked, 0 didn't] expected 'X' after expression
    @1 = @2:: @3((@4)@5, @6);
  → return @1;
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3+0x54);
  → *(unsigned char*)(@3+0x54) = @2(@3+0x54);
[1 worked, 0 didn't] expected 'X' after expression
    @1 = @2:: @3(@4);
  → return @1;
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    *(unsigned char*)(@1+0x54) = @2(@1+0x54);
  → *(unsigned char*)(@1+0x54) = (unsigned char)@2(@1+0x54);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x445250);
  → @1 = @3(0x445250);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x445280);
  → @1 = @3(0x445280);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → @1[16] = @2(@3, @4);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2();
  → @1 = (int)@2();
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x4361f0);
  → @1 = @3(0x4361f0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x433368);
  → @1 = @3(0x433368);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(@3);
  → void*@1 = @2(@3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x43ccc0);
  → @1 = @3(0x43ccc0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x437670);
  → @1 = @3(0x437670);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (**(@2**)(*@3+0x228))(@3);
  → unsigned char @1[16];
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x43a618);
  → @1 = @3(0x43a618);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3+0x78, @4);
  → unsigned char @1[16];@2(@3+0x78, @4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x43d8f0);
  → @1 = @3(0x43d8f0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x443070);
  → @1 = @3(0x443070);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2((long)@3, @4);
  → unsigned char @1[16] = {0};@2((long)@3, @4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x444590);
  → @1 = @3(0x444590);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x443530);
  → @1 = @3(0x443530);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 2;
  → *(unsigned char*)&@1 = (unsigned char)2;
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x442ad8);
  → @1 = @3(0x442ad8);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x444580);
  → @1 = @3(0x444580);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x4430e0);
  → @1 = (void*)@2(0x4430e0);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(@3, 0.0, 0.0, 1.0, &@4);
  → @1 = (long)@2(@3, 0.0, 0.0, 1.0, &@4);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(&@3);
  → unsigned char @1[16];@2(&@3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (@3)(@4)@5;
  → @1[0] = (@3)(@4)@5;
[1 worked, 0 didn't] called object type 'X' (aka 'X') is not a function or function pointer
    @1 = @2();
  → @1 = @2;
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x444480);
  → @1 = @3(0x444480);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x444070);
  → @1 = @3(0x444070);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0xd0);
  → @1 = @3(0xd0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x444490);
  → @1 = @3(0x444490);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (*(@2*)@3)();
  → unsigned char @1[65544];(*(@2*)@3)();
[1 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2(@3);
  → (void*)@1 = @2(@3);
[1 worked, 0 didn't] expected 'X' after expression
    @1 = @2:: @3(*(@4*)(@5+0x20));
  → return @1;
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4+1);
  → unsigned char @1[16] = {0};@2(@3, @4+1);
[1 worked, 0 didn't] expected 'X' after expression
    std:: @1:: @2((char)@3);
  → return(char)@3;
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned char @1[16];@2(@3, @4, @5, @6, @7, @8, @9);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, "", &@5, @6);
  → unsigned char @1[16];@2(@3, @4, "", &@5, @6);
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    int @1 = @2(@3);
  → int @1 = (int)@2(@3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = @2(@3.@4*(double)(@5+-1));
  → @1[0] = @2(@3[0]*(double)(@5+-1));
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → @1[16] = {0};@2();
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@3.@4*9.0);
  → @1 = @2(@3[8]*9.0);
[1 worked, 0 didn't] expected expression
    @1[16] = {0};@2();
  → unsigned char @1[16];@2();
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3((long)@4);
  → @1 = @3((long)@4);
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4341b8);
  → unsigned long long @1 = (unsigned long long)@2(0x4341b8);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, (@4*)(@5+0x37c));
  → @1[16] = {0};@2(@3, (@4*)(@5+0x37c));
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(*(float*)(@3+0x3b8), (@4*)@5);
  → unsigned char @1[16];
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned char @1[16];
  → unsigned char @1[12];
[1 worked, 0 didn't] expected expression
    @1[16] = {0};@2(@3, (@4*)(@5+0x37c));
  → unsigned char @1[16] = {0};@2(@3, (@4*)(@5+0x37c));
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (short*)@2(
  → @1 = @2(
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x425378);
  → unsigned long long @1 = (unsigned long long)@2(0x425378);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1(@2, @3.@4, @3.@5, @6);
  → @1(@2, @3, @6);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (int)@2(
  → @1 = @2(
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (int*)@2((int*)&@3, (int*)&@4);
  → @1 = @2((int*)&@3, (int*)&@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (int*)@2(
  → @1 = @2(
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (**(@2**)(*@3+0x228))(@3);
  → unsigned char @1[16] = {0};(**(@2**)(*@3+0x228))(@3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1.@2 = @3[1];
  → @1[1] = @3[1];
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (@2)@3(
  → @1 = @3(
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2((@3*)@4);
  → @1 = (long)@2((@3*)@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (long)@2((@3*)@4);
  → @1 = @2(@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (long)@2((@3*)@4)
  → @1 = @2(@4)
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@3.@4);
  → @1 = @2(*(unsigned char*)&@3);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (*(@2*)@3)();
  → unsigned char @1[65544] = {0};(*(@2*)@3)();
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = (*
  → unsigned char @1[65544] = {0};(*
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = (@3)0;
  → *(unsigned char*)&@1 = 0;
[1 worked, 0 didn't] variable has incomplete type 'X'
    void std:: @1:: @2(@3*@4)
  → void @2(@3*@4)
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(&@2, @3.@4, @3.@5, @6.@4, @6.@5, @7.@4,
  → @1(&@2, @3[0], @3[8], @6[0], @6[8], @7[0], @7[8]);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (*(@2*)@3)();
  → unsigned char @1[16] = {0};(*(@2*)@3)();
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    (@1.@2, @1.@3, @4
  → (@1, @4
[1 worked, 0 didn't] redefinition of 'X' (part of a line)
    unsigned char @1 =
  → void*@1 =
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    (@1.@2*(
  → (@1*(
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (long*)@2(
  → @1 = @2(
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = (int)@3;
  → @1[0] = (int)@3;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2((long*)&@3, @4.@5);
  → @1 = @2((long*)&@3, @4[0]);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2[16];@3(@4, @5, @6, @7, @8, @9, @10);
  → uint64_t @2[16];@3(@4, @5, @6, @7, @8, @9, @10);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, &@5, &@6, @7);
  → unsigned char @1[16] = {0};@2(@3, @4, &@5, &@6, @7);
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4282a0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4282a0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42eee0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42eee0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42ef00);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42ef00);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4421e0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4421e0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42eed0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42eed0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42fd10);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42fd10);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42fe08);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42fe08);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42fcf0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42fcf0);@3 = @1;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1.@2 = 0x650002;
  → @1[0] = 0x650002;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x444c78);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x444c78);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x444c88);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x444c88);@3 = @1;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(&@2, @3.@4, @3.@5, @6.@4, @6.@5, @7.@4,
  → @1(&@2, @3[0], @3[1], @6[0], @6[1], @7[0]);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = (@3)0;
  → @1[1] = 0;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(&@2, @3.@4, @3.@5, @6.@4, @6.@5, @7.@4,
  → @1(&@2, @3[1], @3[2], @6[1], @6[2], @7[1],
[1 worked, 0 didn't] redefinition of 'X'
    unsigned char @1[16] = {0};@2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned long @1[16];@2(@3, @4, @5, @6, @7, @8, @9);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@3.@4, @3.@5, @6);
  → @1 = @2(&@3[0], &@3[8], @6);
[1 worked, 0 didn't] redefinition of 'X'
    unsigned char @1[16] = {0};@2(@3, @4, @5);
  → unsigned long @1[16];@2(@3, @4, @5);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1[16];@2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned char @1[16];@2(@3, @4, @5, @6, @7, @8, @9);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1[16];@2(@3, @4, @5);
  → unsigned char @1[16];@2(@3, @4, @5);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@1.@3, @1.@4, @5, @6);
  → @1 = @2(@1, @5, @6);
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4433b0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4433b0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4433d0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4433d0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4433e0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4433e0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4433f0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4433f0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x444730);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x444730);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x443410);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x443410);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x444460);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x444460);@3 = @1;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = ((double)@3*@4*2.0*@5)/@6;
  → @1[1] = ((double)@3*@4*2.0*@5)/@6;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    *@1 = @2.@3;
  → *(unsigned char*)@1 = @2[0];
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x425700);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x425700);@3 = @1;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = (double)@2(@1[0].@3, @4);
  → @1[0] = (double)@2(@1[0], @4);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1(*(long*)(@2+0x8b90), @3[0].@4+@5);
  → @1(*(long*)(@2+0x8b90), @5);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(&@3, &@4);
  → @1[16] = {0};@2(&@3, &@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (float)@2(@3);
  → @1 = @2(@3);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (@2*)@3(@4);
  → @1 = (@2*)@3(@4, 0);
[1 worked, 0 didn't] cast to union type from type 'X' (aka 'X') not present in union
    @1 = (@2)@3(@4+0x54);
  → @1 = @3(@4+0x54);
[1 worked, 0 didn't] cast to union type from type 'X' (aka 'X') not present in union (part of a line)
    @1 = (@2)@3(
  → @1 = @3(
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = @3;
  → @1[0] = *(long*)(@1[0]+0x4);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = @3/@4;
  → @1[0] = *(long*)(@1[0]+0x4);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(@2, 0, 12, @3.@4);
  → @1(@2, 0, 12, @3[4]);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    , @1.@2);
  → , @1[4]);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = (**(@2**)(*@3+0x228))(@3);
  → uint64_t @1 = (**(@2**)(*@3+0x228))(@3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (@3)(@4)@5;
  → @1[0] = (long)(@3)(@4)@5;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    0].@1 = (@2
  → 0] = (long)(@2
[1 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    @1 = (*@2)("UTF-8");
  → @1 = @2("UTF-8");
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, "Master dry/wet mix.");
  → @1 = @2(@3, "Master dry/wet mix", 0);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X') (part of a line)
    @1, "Master dry/wet mix.");
  → @1, "Master dry/wet mix", 0);
[1 worked, 0 didn't] no member named 'X' in 'X'
    @1(@2, 0, 8, @2.@3+1);
  → @1(@2, 0, 8, @3+1);
[1 worked, 0 didn't] no member named 'X' in 'X' (part of a line)
    8, @1.@2+
  → 8, @2+
[1 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    @1 = (*@2)(@3, @4, 0, 0, 0);
  → @1 = @2(@3, @4, 0, 0, 0);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1 = 0x640001
  → 0] = 0x640001
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0].@2 = 0x650002;
  → @1[0] = 0x650002;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1 = 0x650002
  → 0] = 0x650002
[1 worked, 0 didn't] redefinition of 'X'
    @1 @2 = @3(@4, @5, @6, @7, @8, @9, @10);
  → @1*@2 = @3(@4, @5, @6, @7, @8, @9, @10);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    0].@1 = 1;@2 = (int)@3[0], @4 = @5(), @2<(int)@4;
  → 0] = 1;@2 = (int)@3[0], @4 = @5(), @2<(@4);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x3ff0000000000000, 8);
  → @1 = (long)@2(0x3ff0000000000000, 8);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    powf();
  → powf(1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    powf(1);
  → powf(1, 0);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(@2, 4, 4, @2.@3+1);
  → @1(@2, 4, 4, @2+1);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    , @1.@2+1
  → , @1+1
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0] = @2(@1[0].@3, 0x3e800000);
  → @1[0] = @2(@1[0], 0x3e800000);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1, 0x3e800000
  → 0], 0x3e800000
[1 worked, 0 didn't] no member named 'X' in 'X'
    @1(@2, 0, 8, @3.@4);
  → @1(@2, 0, 8, @4);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0].@2 = (uint32_t)((@3)>>32);
  → @1[0] = (uint32_t)((@3)>>32);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1 = (
  → 0] = (
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(0);
  → uint64_t @1[1] = {@2(0)};
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(0.95, @3);
  → unsigned long @1 = @2(0.95, @3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    0].@1 = (int)@2;
  → 0] = @2;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (int)@3[0]%100;
  → @1[0] = @3[0]%100;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    0].@1 = (int)@2[
  → 0] = @2[
[1 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    0]);
  → 0], 1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1(0x3f800000, @2, @3, @4, @5);
  → @1(0x3f800000, @2, @3, @4, @5, 0);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1();
  → @1(1);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    return(uint64_t)@1(@2, @3-*(int*)(@2+0x198));
  → return @1(@2, @3-*(int*)(@2+0x198));
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, 1, @7, @8, @9, @10, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 1, @7, @8, @9, @10, 0);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, 2, @7, @8, @9, @10, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 2, @7, @8, @9, @10, 0);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = (long*)@2(@3, @4, @5, @6, @7);
  → ```@1 = (long*)@2((unsigned char*)@3, @4, @5, @6, @7);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1 = (long*)@2(@3,
  → ```@1 = (long*)@2((unsigned char*)@3,
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3, @4, @5, @6, (int*)&@7);
  → unsigned char @1[16] = {0};@2(@3, @4, @5, @6, (int*)&@7);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = *@2;
  → unsigned char @1[16] = {0};
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(0.6060606, @3);
  → unsigned char @1[16] = {0};@2(0.6060606, @3);
[1 worked, 0 didn't] redefinition of 'X'
    @1 @2;
  → unsigned long @2[16];
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1[16];
  → uint64_t @1[16];
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    unsigned long @1[
  → uint64_t @1[
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2();
  → unsigned char @1[1] = {0};@2();
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (double)@2(-@3);
  → @1 = @2(@3, 1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (double)cos();
  → @1 = cos(0);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (float)@2();
  → @1 = (float)@2(1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = @2(*(float*)(@3+0x28)-(float)*(int*)(@3+0x2c));
  → @1 = @2(*(float*)(@3+0x28)-(float)*(int*)(@3+0x2c), 1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    0x2c));
  → 0x2c), 1);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3+0x180, @4);
  → unsigned char @1[1] = {0};@2(@3+0x180, @4);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3, @4);
  → unsigned char @1[1] = {0};@2(@3, @4);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    char*@1;
  → uint64_t @1;
[1 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\x01" :
  → case'\x01' :
[1 worked, 0 didn't] too many arguments to function call, expected N, have N
    @1 = @2(@3, 0, @4, @5, 0x3f, 0, @6, (long)@7, &@8);
  → @1 = @2(@3, 0, @4, @6, 0x3f, 0, (long)@7, &@8);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1(0x3ff0000000000000);
  → return @1(0x3ff0000000000000, 64);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = (@3)@4;
  → @1[0] = (char)@4;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    @1.@2 = (@3)@4
  → @1[0] = (char)@4
[1 worked, 0 didn't] indirection requires pointer operand ('X' invalid)
    *@1(@2, 8, 8, @3+0xdc4);
  → *(long*)(@1(@2, 8, 8, @3+0xdc4));
[1 worked, 0 didn't] indirection requires pointer operand ('X' invalid)
    *@1(@2, 8, 8, @3+0xdc4);
  → @1(@2, 8, 8, @3+0xdc4);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    (**(@1**)(*(long*)((long)&@2.@3+*(long*)(*@4+0x428))+0x10))()
  → (**(@1**)(*(long*)((long)@4[0x428]+*(long*)(*@4+0x428))+0x10))()
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    (**(@1**)(*(long*)((long)&@2.@3+*(long*)(*@4+0x428))+0x18))()
  → (*(@1**)(*(long*)(@4[0x428]+*(long*)(*@4+0x428))+0x18))()
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = (@2*)@3(@4, (long*)((long)&@5.@6+2));
  → @1 = (@2*)@3(@4, (long*)((long)@4[0x6c]+2));
[1 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (long*)((long)@2[0x68]+2);
  → @1 = (long*)((long)@2+0x68*2);
[1 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (@2*)((long)@3[0x68]+3);
  → @1 = (@2*)((long)(@3+0x68)+3);
[1 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    if((((int)@1 = = 0)&& (@2[0x68]+3< = @3))&&
  → if((((int)@1 = = 0)&& ((long*)(@2+0x68)+3< = @3))&&
[1 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    &(@1[0x68]+3
  → &((long*)(@1+0x68)+3
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2((long)@3);
  → unsigned char @1[16] = {0};@2((long)@3);

== retired: 159
[5940 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3);
  → @1 = (void*)@2(@3);
[5922 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (void*)@2(@3);
  → @1 = @2(@3);
[4620 worked, 1 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3);
  → @1 = (long)@2(@3);
[4434 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@3);
  → @1 = @2(@3);
[1935 worked, 1 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2();
  → @1 = (long)@2();
[1905 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2();
  → @1 = @2();
[771 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@1);
  → @1 = (long)@2(@1);
[744 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@1);
  → @1 = @2(@1);
[401 worked, 177 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    @1(@2,
  → @1((unsigned char*)@2,
[230 worked, 135 didn't] passing 'X' to parameter of incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    @1((unsigned char*)@2,
  → @1(@2,
[138 worked, 39 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6);
  → @1((unsigned char*)@2, @3, @4, @5, @6);
[86 worked, 35 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6);
  → @1(@2, @3, @4, @5, @6);
[77 worked, 27 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line) — retired: it and its opposite only undo each other
    return(uint64_t)@1(
  → return @1(
[65 worked, 15 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') (part of a line) — retired: it and its opposite only undo each other
    return @1(
  → return(uint64_t)@1(
[35 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    void*@1 = @2((@3*)(@4+0x88));
  → unsigned char @1 = @2((@3*)(@4+0x88));
[33 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(0x43d890);
  → @1 = (void*)@2(0x43d890);
[33 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(0x436f30);
  → @1 = (void*)@2(0x436f30);
[33 worked, 8 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7);
[32 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    unsigned long @1 = @2(0xd0);
  → unsigned long*@1 = @2(0xd0);
[31 worked, 0 didn't] redefinition of 'X' — retired: it and its opposite only undo each other
    unsigned char @1 = @2((@3*)(@4+0x88));
  → void*@1 = @2((@3*)(@4+0x88));
[30 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    unsigned long*@1 = @2(0xd0);
  → unsigned long @1 = @2(0xd0);
[29 worked, 6 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, @7);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7);
[24 worked, 6 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 0);
[24 worked, 21 didn't] assigning to 'X' from incompatible type 'X' (aka 'X') — retired: it and its opposite only undo each other
    @1 = @2(@3, @4);
  → uint64_t @1 = @2(@3, @4);
[23 worked, 4 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, 1);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 1);
[19 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4);
  → @1 = (long)@2(@3, @4);
[19 worked, 3 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4, @5);
  → return @1(@2, @3, @4, @5);
[19 worked, 7 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7);
  → @1(@2, @3, @4, @5, @6, @7);
[18 worked, 5 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, 0);
  → @1(@2, @3, @4, @5, @6, 0);
[17 worked, 1 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @4, @5);
  → return(uint64_t)@1(@2, @3, @4, @5);
[16 worked, 3 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3);
  → return(uint64_t)@1(@2, @3);
[16 worked, 4 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3);
  → return @1(@2, @3);
[15 worked, 3 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4, @5, @6, @7);
  → return @1(@2, @3, @4, @5, @6, @7);
[14 worked, 2 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @4, @5, @6, @7);
  → return(uint64_t)@1(@2, @3, @4, @5, @6, @7);
[14 worked, 13 didn't] redefinition of 'X' — retired: it and its opposite only undo each other
    uint64_t @1;
  → unsigned long @1;
[12 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (@7)@8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (@7)@8);
[12 worked, 3 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(&@2, &@3);
  → return @1(&@2, &@3);
[11 worked, 1 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(&@2, &@3);
  → return(uint64_t)@1(&@2, &@3);
[10 worked, 5 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, @7);
  → @1 = @2(@3, @4, @5, @6, @7);
[9 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (short*)@2(@3);
  → @1 = @2(@3);
[9 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(0x443fc0);
  → @1 = (int)@2(0x443fc0);
[9 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, 2, 1, 1);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, 2, 1, 1);
[9 worked, 3 didn't] assigning to 'X' from incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    @1 = @2(
  → @1 = (long)@2(
[8 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, @7, 1);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7, 1);
[8 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, (long)@7);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, (long)@7);
[8 worked, 4 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, *(long*)(@6+@7));
  → @1((unsigned char*)@2, @3, @4, @5, *(long*)(@6+@7));
[7 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X' — retired: it and its opposite only undo each other
    long @1 = @2(@3, @4);
  → int @1 = (int)@2(@3, @4);
[7 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (long*)0x0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (long*)0x0);
[7 worked, 3 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, *(long*)(@6+@7));
  → @1(@2, @3, @4, @5, *(long*)(@6+@7));
[6 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (void*)@2();
  → @1 = @2();
[6 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4);
  → return @1(@2, @3, @4);
[6 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, @8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8);
[6 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, @7, &@8);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7, &@8);
[6 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    unsigned long @1;
  → uint64_t @1;
[6 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, (long)@6);
  → @1((unsigned char*)@2, @3, @4, @5, (long)@6);
[6 worked, 2 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, 1);
  → @1(@2, @3, @4, @5, @6, 1);
[6 worked, 4 didn't] redefinition of 'X' — retired: it and its opposite only undo each other
    uint64_t @1;
  → unsigned long*@1;
[5 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(0x42a960);
  → @1 = @2(0x42a960)&0xFFFFFFFFFFFFFFFF;
[5 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @3, @4);
  → return @1(@2, @3, @3, @4);
[5 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, @7, (int*)&@8);
  → @1 = @2(@3, @4, @5, @6, @7, (int*)&@8);
[5 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, @7, 1);
  → @1 = @2(@3, @4, @5, @6, @7, 1);
[5 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    ] = @1(
  → ] = (unsigned char)@1(
[5 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, @7, (int*)&@8);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7, (int*)&@8);
[5 worked, 2 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, @7, &@8);
  → @1 = @2(@3, @4, @5, @6, @7, &@8);
[5 worked, 2 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1[0] = @2(@3+0x180, @4);
  → @1[0] = (unsigned char)@2(@3+0x180, @4);
[4 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, @8));
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8));
[4 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line) — retired: it and its opposite only undo each other
    @1[1] = 0
  → *(@1+1) = 0
[4 worked, 1 didn't] subscripted value is not an array, pointer, or vector — retired: it and its opposite only undo each other
    @1[1] = 0;
  → *(@1+1) = 0;
[3 worked, 0 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @3, @4);
  → return(uint64_t)@1(@2, @3, @3, @4);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (long)(@7+0x2a));
  → @1((unsigned char*)@2, @3, @4, @5, @6, (long)(@7+0x2a));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (long)(@7+0x2a));
  → @1(@2, @3, @4, @5, @6, (long)(@7+0x2a));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, @8, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, 0);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4, @5, @6, @7, @8);
  → return(uint64_t)@1((unsigned char*)@2, @3, @4, @5, @6, @7, @8);
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    return(uint64_t)@1((unsigned char*)@2, @3, @4, @5, @6, @7, @8);
  → return(uint64_t)@1(@2, @3, @4, @5, @6, @7, @8);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (@7)*(@8*)((long)@9+0x27c));
  → @1((unsigned char*)@2, @3, @4, @5, @6, (@7)*(@8*)((long)@9+0x27c));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (@7)*(@8*)(@9+0x27c));
  → @1((unsigned char*)@2, @3, @4, @5, @6, (@7)*(@8*)(@9+0x27c));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (@7)*(@8*)((long)@9+0x27c));
  → @1(@2, @3, @4, @5, @6, (@7)*(@8*)((long)@9+0x27c));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (@7)*(@8*)(@9+0x27c));
  → @1(@2, @3, @4, @5, @6, (@7)*(@8*)(@9+0x27c));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, (long)@6, @7);
  → @1((unsigned char*)@2, @3, @4, @5, (long)@6, @7);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, @8,
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8,
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, @8, @9);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9);
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, (long)@6, @7);
  → @1(@2, @3, @4, @5, (long)@6, @7);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, *@6, @6[1], *@7, @7[1]);
  → @1 = @2((unsigned char*)@3, @4, @5, *@6, @6[1], *@7, @7[1]);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, (@7*)&@8);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, (@7*)&@8);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, (int*)&@8));
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, (int*)&@8));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, (int*)&@8));
  → @1 = @2(@3(@4, @5, @6, @7, (int*)&@8));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, &@7);
  → @1((unsigned char*)@2, @3, @4, @5, @6, &@7);
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, (long)@7);
  → @1 = @2(@3, @4, @5, @6, (long)@7);
[3 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1[0] = (unsigned char)@2(@3+0x180, @4);
  → @1[0] = @2(@3+0x180, @4);
[3 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line) — retired: it and its opposite only undo each other
    ] = (unsigned char)@1(
  → ] = @1(
[3 worked, 1 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, 2, 1, 1);
  → @1(@2, @3, @4, @5, @6, @7, 2, 1, 1);
[3 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, (long)@6,
  → @1((unsigned char*)@2, @3, @4, @5, (long)@6,
[3 worked, 1 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (long*)0x0);
  → @1(@2, @3, @4, @5, @6, (long*)0x0);
[3 worked, 2 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (@7)@8);
  → @1(@2, @3, @4, @5, @6, (@7)@8);
[3 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, 0, 1);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 0, 1);
[2 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2();
  → @1 = (void*)@2();
[2 worked, 0 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @4);
  → return(uint64_t)@1(@2, @3, @4);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, 0);
  → @1(@2, @3, @4, @5, @6, @7, @8, 0);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8));
  → @1 = @2(@3(@4, @5, @6, @7, @8));
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8,
  → @1 = @2(@3(@4, @5, @6, @7, @8,
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9);
  → @1(@2, @3, @4, @5, @6, @7, @8, @9);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, *@6, @6[1], *@7, @7[1]);
  → @1 = @2(@3, @4, @5, *@6, @6[1], *@7, @7[1]);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, (@7*)&@8);
  → @1 = @2(@3, @4, @5, @6, (@7*)&@8);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (int*)@7);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (int*)@7);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, &@7);
  → @1(@2, @3, @4, @5, @6, &@7);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (@7*)&@8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (@7*)&@8);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (@7*)&@8);
  → @1(@2, @3, @4, @5, @6, (@7*)&@8);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, @8, @9,
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9,
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9,
  → @1(@2, @3, @4, @5, @6, @7, @8, @9,
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, (long)@8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, (long)@8);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, (long)@8);
  → @1(@2, @3, @4, @5, @6, @7, (long)@8);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, @8, @9, @10, @11,
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8, @9, @10, @11,
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8, @9, @10, @11,
  → @1 = @2(@3(@4, @5, @6, @7, @8, @9, @10, @11,
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1[0] = @2(@3, @4, @5, @6, @7);
  → @1[0] = @2((unsigned char*)@3, @4, @5, @6, @7);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1[0] = @2((unsigned char*)@3, @4, @5, @6, @7);
  → @1[0] = @2(@3, @4, @5, @6, @7);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (int*)&@7);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (int*)&@7);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (int*)&@7);
  → @1(@2, @3, @4, @5, @6, (int*)&@7);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, *(long*)(@6+@7),
  → @1((unsigned char*)@2, @3, @4, @5, *(long*)(@6+@7),
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, (@5*)&@6, 1);
  → @1 = @2((unsigned char*)@3, @4, (@5*)&@6, 1);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, 0, 1);
  → @1(@2, @3, @4, @5, @6, 0, 1);
[2 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4, @5, &@6, 1);
  → return @1(@2, @3, @4, @5, &@6, 1);
[1 worked, 0 didn't] invalid operands to binary expression ('X' and 'X') — retired: it and its opposite only undo each other
    @1 = @2(0x42a960)&0xFFFFFFFFFFFFFFFF;
  → @1 = @2(0x42a960);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3);
  → @1 = (short*)@2(@3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (void*)@2(0x43d890);
  → @1 = @2(0x43d890);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (void*)@2(0x436f30);
  → @1 = @2(0x436f30);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@3, @4);
  → @1 = @2(@3, @4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (int)@2(0x443fc0);
  → @1 = @2(0x443fc0);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line) — retired: it and its opposite only undo each other
    unsigned long @1 =
  → unsigned long*@1 =
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    int @1 = (int)@2(@3, @4);
  → long @1 = @2(@3, @4);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line) — retired: it and its opposite only undo each other
    unsigned long*@1 =
  → unsigned long @1 =
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line) — retired: it and its opposite only undo each other
    @1 = (long)@2(
  → @1 = @2(
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, 0);
  → @1 = (long)@2(@3, 0);
[1 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1[0] = @2(@3);
  → @1[0] = (unsigned long)@2(@3);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@1, @3);
  → @1 = (long)@2(@1, @3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@3, 0);
  → @1 = @2(@3, 0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1[0] = (unsigned long)@2(@3);
  → @1[0] = @2(@3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@1, @3);
  → @1 = @2(@1, @3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(&@2);
  → return @1(&@2);
[1 worked, 0 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(&@2);
  → return(uint64_t)@1(&@2);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, (long)@6);
  → @1(@2, @3, @4, @5, (long)@6);
[1 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) — retired: it and its opposite only undo each other
    *(@1+1) = 0;
  → @1[1] = 0;
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (int*)@7);
  → @1(@2, @3, @4, @5, @6, (int*)@7);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, *(long*)(@6+@7),
  → @1(@2, @3, @4, @5, *(long*)(@6+@7),
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8);
  → @1(@2, @3, @4, @5, @6, @7, @8);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = (long*)@2(@3, @4, @5, @6, @7);
  → @1 = (long*)@2((unsigned char*)@3, @4, @5, @6, @7);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = (long*)@2((unsigned char*)@3, @4, @5, @6, @7);
  → @1 = (long*)@2(@3, @4, @5, @6, @7);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, (long)@8));
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, (long)@8));
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, (long)@8));
  → @1 = @2(@3(@4, @5, @6, @7, (long)@8));
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, (@5*)&@6, 1);
  → @1 = @2(@3, @4, (@5*)&@6, 1);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, (long)@6,
  → @1(@2, @3, @4, @5, (long)@6,
[1 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    @1(@2,
  → @1((unsigned char*)@2,
[1 worked, 0 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @4, @5, &@6, 1);
  → return(uint64_t)@1(@2, @3, @4, @5, &@6, 1);
[1 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line) — retired: it and its opposite only undo each other
    *(@1+1) = 0
  → @1[1] = 0
[1 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    unsigned long*@1;
  → uint64_t @1;
[1 worked, 5 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' — retired: it and its opposite only undo each other
    uint64_t @1 = @2(@3, @4);
  → @1 = @2(@3, @4);
[1 worked, 5 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (part of a line)
    uint64_t @1 =
  → @1 =
[1 worked, 5 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    @1 = (*@2)(@3
  → @1 = @2(@3
[1 worked, 5 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X') (part of a line)
    @1 @2[
  → unsigned long long @2[
[1 worked, 5 didn't] integer constant expression must have integer type, not 'X'
    case"" :
  → case'\x01' :
```

## build/ideas.txt

```
Ideas the model proposed for kinds of error many functions share, and what
happened to each (newest last). 'adopted' ones are in the build.

== array type 'X' (aka 'X') is not assignable
   24 idea(s), 0 adopted; parked until something changes (or run 8)
   #8 [rejected] rewrite: @1 = @2 ( @3 ) ;  ->  @1 = @2 ( @3 , 0 ) ;
        tested on 7: 0 better, 0 worse
   #9 [rejected] flag: -Wno-error=invalid-assignment
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #10 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #44 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #45 [repeat] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        same as #44
   #46 [rejected] rewrite: @1 = @2 ( 0.6060606 , @3 ) ;  ->  @1 [ 0 ] = @2 ( 0.6060606 , @3 ) [ 0 ] ;
        tested on 1: 0 better, 0 worse
   #65 [no effect] rewrite: * @1 = & @2 ;  ->  * @1 = ( undefined8 * ) & @2 ;
        its 'before' text isn't in any failing line of the examples
   #66 [no effect] rewrite: * @1 = @2 ( @3 ) ;  ->  * @1 = @2 ( @3 ) [ 0 ] ;
        its 'before' text isn't in any failing line of the examples
   #67 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #87 [rejected] flag: -Wno-error=invalid-assignment
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #88 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #89 [repeat] flag: -Wno-error=invalid-assignment
        same as #87
   #108 [no effect] rewrite: * @ 1 = @ 2 ( @ 3 ) ;  ->  * @ 1 = @ 2 ( @ 3 ) [ 0 ] ;
        its 'before' text isn't in any failing line of the examples
   #109 [repeat] rewrite: * @ 1 = @ 2 ( @ 3 ) ;  ->  * @ 1 = @ 2 ( @ 3 ) [ 0 ] ;
        same as #108
   #110 [no effect] rewrite: * @ 1 = ( undefined8 * ) & @ 2 ;  ->  * @ 1 = ( undefined1 * ) & @ 2 ;
        its 'before' text isn't in any failing line of the examples
   #126 [no effect] rewrite: * @ 1 = @ 2 ( @ 3 ) ;  ->  * @ 1 = & @ 2 [ 0 ] ;
        its 'before' text isn't in any failing line of the examples
   #127 [no effect] rewrite: * @ 1 = ( undefined8 * ) & @ 2 ;  ->  * @ 1 = ( undefined1 * ) & @ 2 [ 0 ] ;
        its 'before' text isn't in any failing line of the examples
   #128 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #142 [rejected] flag: -Wno-error=invalid-assignment
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #143 [repeat] flag: -Wno-error=invalid-assignment
        same as #142
   #144 [no effect] rewrite: * @ 1 = @ 2 ( @ 3 ) ;  ->  * @ 1 = @ 2 ( 0 ) ; * ( ( undefined8 * ) & @ 1 ) = @ 3 ;
        its 'before' text isn't in any failing line of the examples
   #164 [rejected] flag: -Wno-error=invalid-assignment
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #165 [repeat] flag: -Wno-error=invalid-assignment
        same as #164
   #166 [no effect] rewrite: * @ 1 = @ 2 ( @ 3 ) ; -> * @ 1 = & @ 2 [ 0 ] ;  ->  * @ 1 = @ 2 ( 0 , sizeof ( undefined1 [ 0 ] ) ) ;
        its 'before' text isn't in any failing line of the examples

== indirection requires pointer operand ('X' (aka 'X') invalid)
   23 idea(s), 0 adopted; parked until something changes (or run 8)
   #29 [rejected] typedef: typedef unsigned long long uint64_t ;
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #30 [rejected] flag: -Wno-error=invalid-operand
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #31 [rejected] rewrite: * @1 ! = 0  ->  ( @1 = = ( undefined8 * ) - 1 ) | | * @1 ! = 0
        tested on 1: 0 better, 1 worse
   #53 [rejected] rewrite: * @1 ! = 0 ;  ->  * @1 > 0 ;
        tested on 1: 0 better, 0 worse
   #54 [no effect] rewrite: * * ( code * ) ( * @1 + 0x20 ) ) ( @1 , @2 , @3 ) ;  ->  * * ( code * ) * ( @1 + 0x20 ) ) ( @1 , @2 , @3 ) ;
        its 'before' text isn't in any failing line of the examples
   #71 [no effect] rewrite: * @ 1 ! = 0  ->  * @ 1 > 0
        its 'before' text isn't in any failing line of the examples
   #72 [rejected] rewrite: * * ( code * * ) ( * @1 + 0x20 ) ) ( @1 , @2 , @3 ) ;  ->  * * ( code * * ) ( @1 + 0x20 , @1 , @2 , @3 ) ;
        tested on 1: 0 better, 0 worse
   #73 [rejected] rewrite: * @1 ! = 0 ;  ->  * ( long * ) @1 ! = 0 ;
        tested on 1: 0 better, 0 worse
   #93 [rejected] rewrite: * @1 ! = 0  ->  * @1 > 0
        tested on 1: 0 better, 0 worse
   #94 [no effect] rewrite: * @ 1 ! = 0 ;  ->  * @ 1 > 0 ;
        its 'before' text isn't in any failing line of the examples
   #95 [rejected] typedef: * local_8 = local_8 + 1 ;
        tested on 8: 0 better, 8 worse, 2 compiling function(s) broke
   #113 [no effect] rewrite: * @1 = @2 ;  ->  @1 = ( long * ) @2 ;
        its 'before' text isn't in any failing line of the examples
   #114 [no effect] rewrite: * * ( code * ) ( * @1 + 0x18 ) ) ( @1 , @2 , @3 ) ;  ->  * ( code * ) * ( * ( @1 + 0x18 ) ) ( * @1 , @2 , @3 ) ;
        its 'before' text isn't in any failing line of the examples
   #115 [rejected] flag: -Wno-error=invalid-operand
        tested on 9: 0 better, 0 worse, 0 compiling function(s) broke
   #132 [no effect] rewrite: * @1 = @1 + 1 ;  ->  * ( long * ) @1 + + ;
        its 'before' text isn't in any failing line of the examples
   #133 [no effect] rewrite: * @ 1 > 0 ;  ->  * ( long * ) @ 1 > 0 ;
        its 'before' text isn't in any failing line of the examples
   #134 [rejected] declare _void_p_void_p: typedef void * _void_p_void_p ( void * , void * ) ;
        shared.h declares no function _void_p_void_p
   #152 [rejected] declare FUN_00001a3c: void FUN_00001a3c ( gh16 , double , undefined8 , double , long * ) ;
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #153 [no effect] rewrite: * * ( code * )  ->  ( code * )
        its 'before' text isn't in any failing line of the examples
   #154 [no effect] rewrite: * @1 = @2 ;  ->  @1 = ( long * ) @2 ;
        its 'before' text isn't in any failing line of the examples
   #173 [no effect] rewrite: * @1 = @2 ;  ->  * @1 = ( long * ) @2 ;
        its 'before' text isn't in any failing line of the examples
   #174 [no effect] rewrite: * * ( code * ) ( * @1 + 0x20 ) )  ->  * * ( code * ) ( * ( long * ) ( @1 + 0x20 ) ) )
        its 'before' text isn't in any failing line of the examples
   #175 [rejected] flag: -Wno-error=indirect-assignment
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke

== member reference base type 'X' (aka 'X') is not a structure or union
   32 idea(s), 0 adopted; parked until something changes (or run 9)
   #5 [rejected] typedef: typedef uint8_t [ 32 ] magic_buffer ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #6 [rejected] flag: -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #7 [repeat] typedef: typedef uint8_t [ 32 ] magic_buffer ;
        same as #5
   #37 [no effect] rewrite: ( long ) ( ( long ) & @1 . magic + 1 )  ->  ( long ) ( & @1 . magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #38 [rejected] flag: -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #39 [repeat] flag: -Wno-error=invalid-offsetof
        same as #38
   #60 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #61 [no effect] rewrite: ( long ) ( & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #84 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #85 [repeat] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        same as #84
   #86 [rejected] flag: -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #106 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #107 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1L )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #123 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1  ->  ( long ) ( ( long ) & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #124 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1L )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #125 [rejected] typedef: typedef char * string ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #140 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( ( long ) & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #141 [rejected] flag: -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #161 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1  ->  ( long ) ( ( long ) & @ 1. magic + 1L
        its 'before' text isn't in any failing line of the examples
   #162 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( ( long ) & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #163 [rejected] typedef: typedef uint8_t string [ sizeof ( uint64_t ) ] ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #180 [rejected] flag -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #181 [no effect] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        its 'before' text isn't in any failing line of the examples
   #182 [repeat] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        same as #181
   #186 [no effect] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        its 'before' text isn't in any failing line of the examples
   #187 [repeat] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        same as #186
   #188 [rejected] flag -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #189 [no effect] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20)" -> "(long)param_6 + *(unsigned long *)(lVar7 + 0x20)"
        its 'before' text isn't in any failing line of the examples
   #193 [no effect] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        its 'before' text isn't in any failing line of the examples
   #194 [no effect] rewrite "*pbVar2 = (byte *)((long)&GD_MACH_HEADER.magic + 1);" -> "*pbVar2 = (byte *)((long)&GD_MACH_HEADER.magic + 1L);"
        its 'before' text isn't in any failing line of the examples
   #198 [rejected] flag -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #199 [rejected] header line typedef uint8_t * byte;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke

== operand of type 'X' where arithmetic or pointer type is required
   37 idea(s), 0 adopted; parked until something changes (or run 9)
   #11 [rejected] flag: -Wno-error=invalid-integer
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #12 [rejected] declare FUN_0013cf80_new: struct streambuf * FUN_0013cf80_new ( struct streambuf * param_1 ) ;
        shared.h declares no function FUN_0013cf80_new
   #13 [repeat] declare FUN_0013cf80_new: struct streambuf * FUN_0013cf80_new ( struct streambuf * param_1 ) ;
        same as #12
   #40 [no effect] rewrite: * @1 * @2 + @3 * @4  ->  ( uint64_t ) ( ( int ) * @1 * @2 + ( int ) @3 * @4 )
        its 'before' text isn't in any failing line of the examples
   #41 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) ) * ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #42 [rejected] declare FUN_0014c8e0_new: uint64_t FUN_0014c8e0_new ( gh16 param_1 , undefined39 param_2 ) ;
        shared.h declares no function FUN_0014c8e0_new
   #62 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) * 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #63 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #64 [rejected] declare FUN_00141c54_new: int FUN_00141c54_new ( uint64_t * param_1 , uint64_t * param_2 ) ;
        shared.h declares no function FUN_00141c54_new
   #81 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #82 [repeat] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        same as #81
   #83 [rejected] flag: -Wno-error=int-conversion
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #103 [rejected] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        shared.h declares no function SoftwareBreakpoint
   #104 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #103
   #105 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #120 [rejected] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        shared.h declares no function SoftwareBreakpoint
   #121 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #120
   #122 [rejected] flag: -Wno-error=int-conversion
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #137 [rejected] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        shared.h declares no function SoftwareBreakpoint
   #138 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #137
   #139 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #137
   #158 [rejected] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        shared.h declares no function SoftwareBreakpoint
   #159 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #158
   #160 [rejected] typedef: typedef void ( * code ) ( void ) ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #176 [rejected] header line typedef float __float2;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #177 [rejected] rewrite "(uint64_t)FUN_000ca8cc(param_1,param_2 - *(int *)(param_1 + 0x198))" -> "(uint64_t)FUN_000ca8cc(param_1,param_2 - (*(int *)(param_1 + 0x198)) & 0xFFFFF
        tested on 1: 0 better, 0 worse
   #178 [rejected] flag -Wno-error=invalid-constexpr-expression
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #179 [rejected] rewrite "(uint64_t)FUN_00141960(param_2,param_3,param_4,param_5,param_6,param_7);" -> "(uint64_t)FUN_00141960((int)(param_2), (int)(param_3), (int)(param_4), (i
        tested on 2: 0 better, 0 worse
   #183 [rejected] header line typedef float __float2;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #184 [rejected] rewrite "(uint64_t)FUN_000ca8cc(param_1,param_2 -*(int *)(param_1 + 0x198))" -> "(uint64_t)FUN_000ca8cc(param_1,param_2 - (*(int *)(param_1 + 0x198)) & 0xFFFFFF
        tested on 1: 0 better, 0 worse
   #185 [rejected] flag -Wno-error=invalid-constexpr-expression
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #190 [no effect] rewrite "*pdVar2 *local_48 + dVar5*dVar4" -> "(uint64_t)((int)*pdVar2 * local_48 + (int)dVar5 *dVar4)"
        its 'before' text isn't in any failing line of the examples
   #191 [rejected] rewrite "(uint64_t)FUN_000ca8cc(param_1,param_2 -*(int *)(param_1 + 0x198))" -> "(uint64_t)FUN_000ca8cc(param_1,param_2 - (*(int *)(param_1 + 0x198)) & 0xFFFFFF
        tested on 1: 0 better, 0 worse
   #192 [rejected] header line typedef struct __float2 float2;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #195 [rejected] header line typedef float __float2;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #196 [rejected] rewrite "(uint64_t)FUN_000ca8cc(param_1,param_2 -*(int *)(param_1 + 0x198))" -> "(uint64_t)FUN_000ca8cc(param_1, (int)(param_2 - (*(int *)(param_1 + 0x198))));"
        tested on 1: 0 better, 0 worse
   #197 [rejected] flag -Wno-error=invalid-constexpr-expression
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke

== passing 'X' (aka 'X') to parameter of incompatible type 'X'
   21 idea(s), 0 adopted; parked until something changes (or run 8)
   #1 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #2 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #1
   #3 [rejected] flag: -Wno-error=implicit-int
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #4 [rejected] typedef: typedef unsigned char gh16 ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #35 [rejected] flag: -Wno-error=implicit-int
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #36 [repeat] flag: -Wno-error=implicit-int
        same as #35
   #58 [rejected] typedef: typedef unsigned char gh16 ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #59 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #78 [rejected] flag: -Wno-error=implicit-int
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #79 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #80 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( gh16 [ 8 ] )
        its 'before' text isn't in any failing line of the examples
   #100 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #101 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #100
   #102 [rejected] typedef: typedef unsigned char gh16 ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #118 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #119 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #118
   #135 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #136 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #135
   #155 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #156 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #155
   #157 [rejected] flag: -Wno-error=invalid-const-ref
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke

== passing 'X' to parameter of incompatible type 'X'
   6 idea(s), 0 adopted; parked until something changes (or run 6)
   #149 [rejected] flag: -Wno-error=invalid-const-ref
        tested on 9: 0 better, 0 worse, 0 compiling function(s) broke
   #150 [rejected] typedef: typedef unsigned char gh16 ;
        tested on 9: 0 better, 9 worse, 2 compiling function(s) broke
   #151 [repeat] typedef: typedef unsigned char gh16 ;
        same as #150
   #170 [no effect] rewrite: float @1 = ( float ) powf ( @2 , 0x3e4ccccd ) ;  ->  float @1 = ( float ) pow ( @2 , 0x3e4ccccd ) ;
        its 'before' text isn't in any failing line of the examples
   #171 [no effect] rewrite: @1 = fmod ( @2 , ( double ) ( long ) * ( int * ) ( @3 + 0x298 ) + - 1.0 ) ;  ->  @1 = fmod ( @2 , ( double ) ( long ) * ( int * ) ( @3 + 0x298 ) ) ;
        its 'before' text isn't in any failing line of the examples
   #172 [rejected] flag: -Wno-error=invalid-const-ref
        tested on 10: 0 better, 0 worse, 0 compiling function(s) broke

== passing 'X' to parameter of incompatible type 'X' (aka 'X')
   24 idea(s), 0 adopted; parked until something changes (or run 8)
   #23 [rejected] flag: -Wno-error=invalid-constexpr-expression
        tested on 14: 0 better, 0 worse, 0 compiling function(s) broke
   #24 [rejected] declare FUN_000037fc: undefined8 FUN_000037fc ( undefined8 )
        tested on 14: 0 better, 14 worse, 2 compiling function(s) broke
   #25 [rejected] typedef: typedef uint64_t gh16 ;
        tested on 14: 0 better, 14 worse, 2 compiling function(s) broke
   #50 [rejected] rewrite: @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , CONCAT44 ( @6 , @7 ) ) ;  ->  @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , ( undefined1 ) CONCAT44 ( @6 , @7 ) ) ;
        tested on 2: 0 better, 0 worse
   #51 [no effect] rewrite: @ 1 ( 0x3f800000 , @ 2 , @ 3 , @ 4 , @ 5 , CONCAT44 ( @ 6 , @ 7 ) ) ;  ->  @ 1 ( 0x3f800000 , @ 2 , @ 3 , @ 4 , @ 5 , ( undefined1 ) CONCAT44 ( @ 6 , @
        its 'before' text isn't in any failing line of the examples
   #52 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 11: 0 better, 0 worse, 0 compiling function(s) broke
   #68 [rejected] rewrite: CONCAT44 ( @1 , @2 )  ->  CONCAT44 ( ( undefined1 ) @1 , @2 )
        tested on 2: 0 better, 0 worse
   #69 [rejected] rewrite: @1 = @2 ( @3 , @4 , @5 ) ;  ->  @1 = @2 ( ( undefined8 ) @3 , @4 , @5 ) ;
        tested on 3: 0 better, 0 worse
   #70 [rejected] declare FUN_000052cb8: void FUN_000052cb8 ( undefined1 * param_1 , undefined8 local_a8 , undefined8 unused_param ) ;
        shared.h declares no function FUN_000052cb8
   #90 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 11: 0 better, 0 worse, 0 compiling function(s) broke
   #91 [repeat] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        same as #90
   #92 [rejected] declare FUN_00052cb8: void FUN_00052cb8 ( undefined1 * param_1 , undefined8 local_a8 , undefined8 unused_param ) ;
        tested on 11: 0 better, 0 worse, 1 compiling function(s) broke
   #111 [rejected] rewrite: @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , CONCAT44 ( @6 , @7 ) ) ;  ->  @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , ( undefined1 ) CONCAT44 ( @6 , @7 ) ) ;
        tested on 3: 0 better, 0 worse
   #112 [rejected] declare GH16: undefined8 GH16 ( undefined1 param_1 ) ;
        shared.h declares no function GH16
   #129 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 12: 0 better, 0 worse, 0 compiling function(s) broke
   #130 [repeat] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        same as #129
   #131 [rejected] typedef: typedef unsigned long long gh16 ;
        tested on 12: 0 better, 12 worse, 2 compiling function(s) broke
   #145 [rejected] rewrite: @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , CONCAT44 ( @6 , @7 ) ) ;  ->  @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , ( undefined1 ) CONCAT44 ( @6 , @7 ) ) ;
        tested on 3: 0 better, 0 worse
   #146 [rejected] declare GH16: undefined8 GH16 ( undefined1 param_1 ) ;
        shared.h declares no function GH16
   #147 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 12: 0 better, 0 worse, 0 compiling function(s) broke
   #148 [rejected] declare GH16: undefined8 GH16 ( undefined8 param_1 ) ;
        shared.h declares no function GH16
   #167 [rejected] rewrite: @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , CONCAT44 ( @6 , @7 ) ) ;  ->  @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , ( undefined1 ) CONCAT44 ( @6 , @7 ) ) ;
        tested on 3: 0 better, 0 worse
   #168 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 12: 0 better, 0 worse, 0 compiling function(s) broke
   #169 [no effect] rewrite: @ 1 ( 0x3f800000 , @ 2 , @ 3 , @ 4 , @ 5 , CONCAT44 ( @ 6 , @ 7 ) ) ;  ->  @ 1 ( 0x3f800000 , @ 2 , @ 3 , @ 4 , @ 5 , CONCAT44 ( ( undefined1 ) @ 6 , (
        its 'before' text isn't in any failing line of the examples

== redefinition of 'X'
   2 idea(s), 0 adopted; parked until something changes (or run 4)
   #19 [rejected] typedef: typedef struct { undefined6 field ; } type_undefined6_t ;
        tested on 19: 0 better, 0 worse, 0 compiling function(s) broke
   #49 [rejected] rewrite: undefined6 @1 ;  ->  uint64_t @1 = 0 ;
        tested on 8: 0 better, 0 worse

== redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
   5 idea(s), 0 adopted; parked until something changes (or run 4)
   #16 [rejected] typedef: typedef uint64_t uint64_t ;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #17 [no effect] rewrite: undefined1 @1 [ 16 ] ; undefined1 @2 [ 16 ] ;  ->  uint64_t @1 [ 16 ] ; uint64_t @2 [ 16 ] ;
        its 'before' text isn't in any failing line of the examples
   #18 [rejected] typedef: typedef uint64_t * undefined8 * ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #47 [rejected] flag: -Wno-error=declaration-requires-type-id
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #48 [rejected] typedef: typedef uint64_t undefined8 ;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke

== redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
   3 idea(s), 0 adopted; parked until something changes (or run 4)
   #14 [rejected] typedef: typedef ulonglong uint64_t ;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #15 [rejected] typedef: typedef unsigned long long uint64_t ;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #43 [rejected] rewrite: int @1 ;  ->  uint64_t @1 ;
        tested on 10: 0 better, 0 worse

== too few arguments to function call, expected N, have N
   3 idea(s), 0 adopted; parked until something changes (or run 3)
   #20 [rejected] flag: -Wno-error=missing-argument
        tested on 18: 0 better, 0 worse, 0 compiling function(s) broke
   #21 [rejected] declare log10fWrapper: float log10fWrapper ( void ) ;
        shared.h declares no function log10fWrapper
   #22 [repeat] flag: -Wno-error=missing-argument
        same as #20

== too few arguments to function call, single argument 'X' was not specified
   3 idea(s), 0 adopted; parked until something changes (or run 3)
   #32 [rejected] declare CFRelease: void CFRelease ( void * param_1 ) ;
        shared.h declares no function CFRelease
   #33 [repeat] declare CFRelease: void CFRelease ( void * param_1 ) ;
        same as #32
   #34 [rejected] declare CFRelease: int CFRelease ( void * param_1 ) ;
        shared.h declares no function CFRelease

== too many arguments to function call, expected N, have N
   16 idea(s), 0 adopted; parked until something changes (or run 8)
   #26 [rejected] declare CFStringGetCharacters: void CFStringGetCharacters ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar * dstPtr
        shared.h declares no function CFStringGetCharacters
   #27 [rejected] declare CFStringGetBytes: void CFStringGetBytes ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar * dstPtr ) ;
        shared.h declares no function CFStringGetBytes
   #28 [rejected] flag: -Wno-error=missing-braces
        tested on 10: 0 better, 0 worse, 0 compiling function(s) broke
   #55 [rejected] declare CFStringGetCharacters: void CFStringGetCharacters ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar * dstPtr
        shared.h declares no function CFStringGetCharacters
   #56 [repeat] declare CFStringGetCharacters: void CFStringGetCharacters ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar * dstPtr
        same as #55
   #57 [rejected] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        shared.h declares no function CFStringGetCharactersAndLength
   #74 [rejected] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        shared.h declares no function CFStringGetCharactersAndLength
   #75 [rejected] declare CFStringGetBytesAndLength: void CFStringGetBytesAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar 
        shared.h declares no function CFStringGetBytesAndLength
   #76 [rejected] typedef: # define CFStringGetBytesAndLength CFStringGetBytes
        tested on 9: 0 better, 0 worse, 0 compiling function(s) broke
   #77 [repeat] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        same as #74
   #96 [rejected] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        shared.h declares no function CFStringGetCharactersAndLength
   #97 [rejected] flag: -Wno-error=extra-arg
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #98 [rejected] typedef: # define CFStringGetBytesAndLength CFStringGetBytes
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #99 [rejected] typedef: # define CFStringGetCharactersAndLength CFStringGetBytes
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #116 [rejected] declare CFStringGetBytesAndLength: void CFStringGetBytesAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar 
        shared.h declares no function CFStringGetBytesAndLength
   #117 [rejected] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        shared.h declares no function CFStringGetCharactersAndLength
```

## build/test/test_report.txt

```
Run test: the rebuilt plugin against the original (2026-10-24 19:54:03)

original: Original.component
  architectures: x86_64, arm64; tested as arm64
rebuilt:  /Users/user?/name1decomp/fastpass 3/build_c/program.dylib (arm64)

packaged the rebuilt program as /Users/user?/name1decomp/fastpass 3/build_c/test/run-_lqzbx8k/Rebuilt.component (deleted after the test), with the original's Info.plist (35 privacy stand-in(s) applied) and its Resources folder linked in

== component Illformed: Name1 (aumf/igl2/DBlu)
factory: original AUPluginFactory; rebuilt AUPluginFactory (as in the original)
rebuilt plugin, loading: FAILED
crashed (SIGSEGV) during: load executable
    CRASH signal=11 (SIGSEGV: bad memory access) address=0x8
    CRASH stack:
    0   aharness_host-arm64-325db53723      0x0000000104b5d2a4 on_crash + 196
    1   libsystem_platform.dylib            0x000000018d081744 _sigtramp + 56
    2   program                             0x000000010aef2664 FUN_0020e3a0 + 16
    3   program                             0x000000010aef2600 FUN_0020e2fc + 12
    4   program                             0x000000010aef25bc FUN_0020e27c + 28
    5   program                             0x000000010aeef328 FUN_0020bbe4 + 24
    6   program                             0x000000010aec7d8c FUN_001f04ac + 36
    7   program                             0x000000010aec7e88 FUN_001f05ac + 12
    8   program                             0x000000010b208718 gd_relocate + 4360
    9   dyld                                0x000000018ccdaa28 ___ZZNK5dyld46Loader25findAndRunAllInitializersERNS_12RuntimeStateEENK3$_0clEv_block_invoke + 180
    10  dyld                                0x000000018cce5a8c ___ZNK5dyld313MachOAnalyzer18forEachInitializerER11DiagnosticsRKNS0_15VMAddrConverterEU13block_pointerFvjEPKv_block_invoke.204 + 320
    11  dyld                                0x000000018cd25fac ___ZNK6mach_o12UnsafeHeader14forEachSectionEU13block_pointerFvRKNS0_11SectionInfoERbE_block_invoke + 312
    12  dyld                                0x000000018cd229a4 _ZNK6mach_o12UnsafeHeader18forEachLoadCommandEU13block_pointerFvPK12load_commandRbE + 208
    13  dyld                                0x000000018cd2424c _ZNK6mach_o12UnsafeHeader14forEachSectionEU13block_pointerFvRKNS0_11SectionInfoERbE + 124
    14  dyld                                0x000000018cce5580 _ZNK5dyld313MachOAnalyzer18forEachInitializerER11DiagnosticsRKNS0_15VMAddrConverterEU13block_pointerFvjEPKv + 516
    15  dyld                                0x000000018ccd5394 _ZNK5dyld46Loader25findAndRunAllInitializersERNS_12RuntimeStateE + 528
    16  dyld                                0x000000018cccdcd0 _ZNK5dyld416JustInTimeLoader15runInitializersERNS_12RuntimeStateE + 36
    17  dyld                                0x000000018ccd5ab0 _ZNK5dyld46Loader23runInitializersBottomUpERNS_12RuntimeStateERN3lsl6VectorI18AuthenticatedValueIPKS0_EEESA_ + 568
    18  dyld                                0x000000018ccdaac0 _ZZNK5dyld46Loader38runInitializersBottomUpPlusUpwardLinksERNS_12RuntimeStateEENK3$_0clEv + 116
    19  dyld                                0x000000018ccd5d98 _ZNK5dyld46Loader38runInitializersBottomUpPlusUpwardLinksERNS_12RuntimeStateE + 716
    20  dyld                                0x000000018cca42cc _ZZN5dyld44APIs11dlopen_fromEPKciPvENK3$_0clEv + 2320
    21  dyld                                0x000000018cc98004 _ZN5dyld44APIs11dlopen_fromEPKciPv + 1116
    22  dyld                                0x000000018cc97b04 _ZN5dyld44APIs6dlopenEPKci + 120
    23  CoreFoundation                      0x000000018d16c750 _CFBundleDlfcnLoadFramework + 156
    24  CoreFoundation                      0x000000018d1c2c20 _CFBundleLoadExecutableAndReturnError + 472
    25  aharness_host-arm64-325db53723      0x0000000104b5d628 open_unit + 204
    26  aharness_host-arm64-325db53723      0x0000000104b5c8c8 main + 248
    27  dyld                                0x000000018ccac4e4 start + 6992
    ����*k       /usr/lib/dyld
    rebuilt functions in the stack (innermost first): FUN_0020e3a0 (funcs/_FUN_0020e3a0.cpp), FUN_0020e2fc (funcs/_FUN_0020e2fc.cpp), FUN_0020e27c (funcs/_FUN_0020e27c.cpp), FUN_0020bbe4 (funcs/_FUN_0020bbe4.cpp), FUN_001f04ac (funcs/_FUN_001f04ac.cpp), FUN_001f05ac (funcs/_FUN_001f05ac.cpp)
    (an address near zero: a null pointer, often a global or object the rebuilt program never set up)
    code of FUN_0020e3a0 (funcs/_FUN_0020e3a0.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0020e3a0(void)
         4 | {
         5 |   undefined8 *puVar1;
         6 | 
         7 |   puVar1 = (undefined8 *)FUN_0020e24c();
         8 |   puVar1[1] = 0;
         9 |   *puVar1 = 0;
        10 |   puVar1[2] = 0;
        11 |   return;
        12 | }
        13 | 
    code of FUN_0020e2fc (funcs/_FUN_0020e2fc.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0020e2fc(void)
         4 | {
         5 |   FUN_0020e3a0();
         6 |   return;
         7 | }
         8 | 
    code of FUN_0020e27c (funcs/_FUN_0020e27c.cpp):
         1 | #include "shared.h"
         2 | 
         3 | undefined8 FUN_0020e27c(undefined8 param_1)
         4 | {
         5 |   FUN_0020e2c8();
         6 |   FUN_0020e2ec();
         7 |   FUN_0020e2fc();
         8 |   return param_1;
         9 | }
        10 | 
    code of FUN_0020bbe4 (funcs/_FUN_0020bbe4.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0020bbe4(undefined8 param_1)
         4 | {
         5 |   FUN_0020e27c(param_1);
         6 |   return;
         7 | }
         8 | 
    code of FUN_001f04ac (funcs/_FUN_001f04ac.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_001f04ac(void)
         4 | {
         5 |   FUN_0020bbe4(&GD_DAT_0045f5e8);
         6 |   __cxa_atexit(GD_PTR__string_004240b0,&GD_DAT_0045f5e8,0);
         7 |   return;
         8 | }
         9 | 
    code of FUN_001f05ac (funcs/_FUN_001f05ac.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_001f05ac(void)
         4 | {
         5 |   FUN_001f04ac();
         6 |   FUN_001f04ec();
         7 |   FUN_001f052c();
         8 |   FUN_001f056c();
         9 |   return;
        10 | }
        11 | 
    the rebuilt plugin's load steps (GD_DEBUG):
      initializer 8/91: FUN_0006bd14
      initializer 9/91: FUN_0006d484
      initializer 10/91: FUN_00091eb4
      initializer 11/91: FUN_00096f44
      initializer 12/91: FUN_00096f7c
      initializer 13/91: FUN_0009720c
      initializer 14/91: FUN_000a5800
      initializer 15/91: FUN_000abe14
      initializer 16/91: FUN_000b0e24
      initializer 17/91: FUN_000b4380
      initializer 18/91: FUN_000b6238
      initializer 19/91: FUN_000b6270
      initializer 20/91: FUN_000b62a8
      initializer 21/91: FUN_000bc4ec
      initializer 22/91: FUN_000c54d0
      initializer 23/91: FUN_000c6ce8
      initializer 24/91: FUN_000f8dcc
      initializer 25/91: FUN_0010a5fc
      initializer 26/91: FUN_00112498
      initializer 27/91: FUN_0011288c
      initializer 28/91: FUN_0011b3cc
      initializer 29/91: FUN_0011b404
      initializer 30/91: FUN_00127608
      initializer 31/91: FUN_00127640
      initializer 32/91: FUN_0012928c
      initializer 33/91: FUN_00129824
      initializer 34/91: FUN_0012db44
      initializer 35/91: FUN_0012f118
      initializer 36/91: FUN_0012f150
      initializer 37/91: FUN_0012f6d0
      initializer 38/91: FUN_0013235c
      initializer 39/91: FUN_001549a0
      initializer 40/91: FUN_001549d8
      initializer 41/91: FUN_00155ec8
      initializer 42/91: FUN_00156ea0
      initializer 43/91: FUN_00156ed8
      initializer 44/91: FUN_00156f10
      initializer 45/91: FUN_001676bc
      initializer 46/91: FUN_00170a1c
      initializer 47/91: FUN_00171830
      initializer 48/91: FUN_001756c4
      initializer 49/91: FUN_001a86a4
      initializer 50/91: FUN_001aca8c
      initializer 51/91: FUN_001bbd0c
      initializer 52/91: FUN_001c1460
      initializer 53/91: FUN_001c1744
      initializer 54/91: FUN_001c177c
      initializer 55/91: FUN_001c2280
      initializer 56/91: FUN_001c22d4
      initializer 57/91: FUN_001c2328
      initializer 58/91: FUN_001c2364
      initializer 59/91: FUN_001cf594
      initializer 60/91: FUN_001d8fec
      initializer 61/91: FUN_001da7f4
      initializer 62/91: FUN_001e326c
      initializer 63/91: FUN_001e4cbc
      initializer 64/91: FUN_001e4dd8
      initializer 65/91: FUN_001e9544
      initializer 66/91: FUN_001eb9ac
      initializer 67/91: FUN_001f05ac
    registers when it crashed (the ones that point into the rebuilt program explained):
       x0 = 0x0000000000000000  (zero)
       x1 = 0x0000000000000000  (zero)
       x2 = 0x00000000000120a8
       x3 = 0x000000016b2a100b
       x4 = 0x000000010b21f7d4  in the rebuilt program: zoom_ + 0x145e0
       x5 = 0x000000016b2a1540
       x6 = 0x000000000000000a  (near zero)
       x7 = 0x0000000000000000  (zero)
       x8 = 0x0000000000000000  (zero)
       x9 = 0x00000000000014b8  (near zero)
      x10 = 0x0000000000000002  (near zero)
      x11 = 0x00000000fffffffd
      x12 = 0x0000000000000000  (zero)
      x13 = 0x0000000000000000  (zero)
      x14 = 0x0000000000000000  (zero)
      x15 = 0x0000000000000000  (zero)
      x16 = 0x000000018d034618
      x17 = 0x00000001fb0f7228
      x18 = 0x0000000000000000  (zero)
      x19 = 0x000000016b2a1be8
      x20 = 0x000000010b207610  in the rebuilt program: gd_relocate + 0x0
      x21 = 0x00000001f9801360
      x22 = 0x000000010b20c0a4  in the rebuilt program: zoom_ + 0xeb0
      x23 = 0x000000010abe0118
      x24 = 0x0000000000000006  (near zero)
      x25 = 0x00000000000000a0  (near zero)
      x26 = 0x000000010abe0248
      x27 = 0x000000010abe00c0
      x28 = 0x0000000000000010  (near zero)
       fp = 0x000000016b2a14b0
       lr = 0x000000010aef2664  in the rebuilt program: FUN_0020e3a0 + 0x10
       sp = 0x000000016b2a14a0
       pc = 0x000000010aef266c  in the rebuilt program: FUN_0020e3a0 + 0x18
    the rebuilt frames as source lines:
        2: FUN_0020e3a0 (in program.dylib) (_FUN_0020e3a0.cpp:7)
        3: FUN_0020e2fc (in program.dylib) (_FUN_0020e2fc.cpp:6)
        4: FUN_0020e27c (in program.dylib) (_FUN_0020e27c.cpp:8)
        5: FUN_0020bbe4 (in program.dylib) (_FUN_0020bbe4.cpp:6)
        6: FUN_001f04ac (in program.dylib) (_FUN_001f04ac.cpp:5)
        7: FUN_001f05ac (in program.dylib) (_FUN_001f05ac.cpp:6)
        8: gd_relocate (in program.dylib) (ghidra_data.c:30096)
       pc: FUN_0020e3a0 (in program.dylib) (_FUN_0020e3a0.cpp:8)
       lr: FUN_0020e3a0 (in program.dylib) (_FUN_0020e3a0.cpp:7)
    where it crashed: FUN_0020e3a0 line 8: puVar1[1] = 0;
    called just before the crash: FUN_0020e24c (funcs/_FUN_0020e24c.cpp)
         1 | #include "shared.h"
         2 | 
         3 | undefined8 FUN_0020e24c(void)
         4 | {
         5 |   undefined8 uVar1;
         6 | 
         7 |   uVar1 = FUN_0020e26c();
         8 |   return uVar1;
         9 | }
        10 | 
    Ghidra's pseudocode of FUN_0020e24c:
      undefined8 FUN_0020e24c(void)
      
      {
        undefined8 uVar1;
        
        uVar1 = FUN_0020e26c();
        return uVar1;
      }
    Ghidra's pseudocode of FUN_0020e3a0:
      void FUN_0020e3a0(void)
      
      {
        undefined8 *puVar1;
        
        puVar1 = (undefined8 *)FUN_0020e24c();
        puVar1[1] = 0;
        *puVar1 = 0;
        puVar1[2] = 0;
        return;
      }
    Ghidra's pseudocode of FUN_0020e2fc:
      void FUN_0020e2fc(void)
      
      {
        FUN_0020e3a0();
        return;
      }
    Ghidra's pseudocode of FUN_0020e27c:
      undefined8 FUN_0020e27c(undefined8 param_1)
      
      {
        FUN_0020e2c8();
        FUN_0020e2ec();
        FUN_0020e2fc();
        return param_1;
      }
    Ghidra's pseudocode of FUN_0020bbe4:
      void FUN_0020bbe4(undefined8 param_1)
      
      {
        FUN_0020e27c(param_1);
        return;
      }
    data FUN_001f04ac uses:
      GD_DAT_0045f5e8: block __bss + 0x14b8; original 0x45f5e8, Ghidra's DAT_0045f5e8; the original has there: 00 00 00 00 00 00 00 00; no fix-up there
      GD_PTR__string_004240b0: block __got + 0xb0; original 0x4240b0, Ghidra's PTR_~string_004240b0; the original has there: 7c 5e 38 00 00 00 00 00; fixed up at load: function -> 385e7c ~string
    Ghidra's pseudocode of FUN_001f04ac:
      void FUN_001f04ac(void)
      
      {
        FUN_0020bbe4(&DAT_0045f5e8);
        ___cxa_atexit(PTR__string_004240b0,&DAT_0045f5e8,0);
        return;
      }
    Ghidra's pseudocode of FUN_001f05ac:
      void FUN_001f05ac(void)
      
      {
        FUN_001f04ac();
        FUN_001f04ec();
        FUN_001f052c();
        FUN_001f056c();
        return;
      }

the rebuilt plugin didn't load: crashed (SIGSEGV) during: load executable
```

## rewrite/data_placeholders.txt

```
Data the code names that the data export doesn't have: each gets a zero-filled
placeholder (it compiles, but reads zeros). Where it is, to see what the export misses:

DAT_800000008: not in any exported block; nearest: __LINKEDIT ends at 0x8a4000, nothing after
```

## rewrite/data_unresolved_pointers.txt

```
Pointers stored in the data that point outside every exported block: they keep
the original program's address, which doesn't exist in the rebuilt one.

at 881a73 -> 3de0
at 881aa9 -> 477c
at 881b3e -> 6b80
at 881b44 -> 6d50
at 881d44 -> f5a0
at 882040 -> 1ffbc
at 884451 -> fff8c
```

## rewrite/data_blocks.txt

```
The data export's blocks (name, start, size, writable, bytes exported):

__TEXT  0x0  6716  -  bytes
__text  0x1a3c  3685916  -  bytes
__objc_methlist  0x38a020  1724  -  bytes
__gcc_except_tab  0x38a6dc  143220  -  bytes
__const  0x3ad650  242827  -  bytes
__cstring  0x3e8adb  126659  -  bytes
__ustring  0x40799e  306  -  bytes
__objc_methname  0x407ad0  9664  -  bytes
__objc_classname  0x40a090  319  -  bytes
__objc_methtype  0x40a1cf  2629  -  bytes
__unwind_info  0x40ac14  101004  -  bytes
__eh_frame  0x4236a0  2400  -  bytes
__got  0x424000  624  w  bytes
__mod_init_func  0x424270  728  w  bytes
__DATA_CONST  0x424548  8  w  bytes
__const  0x424550  171664  -  bytes
__cfstring  0x44e3e0  1376  w  bytes
__objc_classlist  0x44e940  72  w  bytes
__objc_protolist  0x44e988  32  w  bytes
__objc_imageinfo  0x44e9a8  5720  w  bytes
__la_symbol_ptr  0x450000  2816  w  bytes
__objc_const  0x450b00  5544  w  bytes
__objc_selrefs  0x4520a8  3136  -  bytes
__objc_classrefs  0x452ce8  408  -  bytes
__objc_superrefs  0x452e80  80  -  bytes
__objc_ivar  0x452ed0  140  w  bytes
__DATA  0x452f5c  4  w  bytes
__objc_data  0x452f60  720  -  bytes
__data  0x453230  44800  w  bytes
__bss  0x45e130  7888  w  bytes
__bss  0x460000  4266456  w  zero-filled
__common  0x8719d8  27648  w  zero-filled
__DATA  0x8785d8  14888  w  zero-filled
__LINKEDIT  0x87c000  160000  -  bytes
__LINKEDIT  0x8a3100  3840  -  zero-filled
```

## rewrite/lost_returns.txt

```
Functions Ghidra says return nothing, whose callers use what they return, and that
have no call at the end whose value they could return: each returns 0 here. If the
real one returns a pointer (often what it was given), callers that use it break.

FUN_00003df4
FUN_00004500
FUN_00004520
FUN_00004540
FUN_00004960
FUN_000049b4
FUN_00004ce8
FUN_00005170
FUN_00006e90
FUN_000076a4
FUN_00008830
FUN_0000a9c0
FUN_0000bbd8
FUN_0000bfdc
FUN_0000c198
FUN_0000c268
FUN_0000c324
FUN_0000c448
FUN_0000c468
FUN_0000ce38
FUN_0000dd2c
FUN_0000f258
FUN_0000f278
FUN_0000f368
FUN_0000f388
FUN_0000f930
FUN_00016738
FUN_000167a4
FUN_00016810
FUN_00016864
FUN_00016ef0
FUN_000179b4
FUN_000188b0
FUN_00018d68
FUN_00018dec
FUN_0001929c
FUN_000196c4
FUN_0001a464
FUN_0001bf00
FUN_00020bc0
FUN_00020d60
FUN_00020d80
FUN_00020da0
FUN_00020dc0
FUN_00020e88
FUN_00020fc8
FUN_00023c5c
FUN_00028590
FUN_0002ab4c
FUN_0002ebe0
FUN_00030bd0
FUN_00030bf0
FUN_0003188c
FUN_00031f0c
FUN_00033578
FUN_000351ec
FUN_0003588c
FUN_000359dc
FUN_00037544
FUN_00037564
FUN_00037584
FUN_000376e8
FUN_00038d34
FUN_0003ce54
FUN_0003cea8
FUN_0003cefc
FUN_0003cf50
FUN_0003dae0
FUN_0004249c
FUN_00042bc8
FUN_000436b8
FUN_00045264
FUN_00047f8c
FUN_00047fe8
FUN_0004a74c
FUN_0004afd4
FUN_0004fa4c
FUN_0004faa0
FUN_00052100
FUN_00055144
FUN_00055194
FUN_000551b4
FUN_000552b8
FUN_0005537c
FUN_00056abc
FUN_00056df4
FUN_00056e14
FUN_00056f14
FUN_00059f20
FUN_0005b134
FUN_00067a58
FUN_00067e0c
FUN_00067e38
FUN_00067efc
FUN_00067f0c
FUN_0006804c
FUN_0006821c
FUN_000682a0
FUN_000685fc
FUN_00068a4c
FUN_00068cc4
FUN_00068cf8
FUN_00068d2c
FUN_00068d6c
FUN_00069828
FUN_00069854
FUN_00069898
FUN_000698a8
FUN_00069914
FUN_00069a30
FUN_00069a40
FUN_00069b18
FUN_00069b7c
FUN_0006a270
FUN_0006a2a4
FUN_0006a2d4
FUN_0006ad44
FUN_0006ad74
FUN_0006ae4c
FUN_0006b354
FUN_0006b48c
FUN_0006b66c
FUN_0006b6a0
FUN_0006b6d4
FUN_0006b714
FUN_0006b8a8
FUN_0006baa4
FUN_0006bae4
FUN_0006c4b4
FUN_0006c4e4
FUN_0006c5bc
FUN_0006cac4
FUN_0006cbfc
FUN_0006cddc
FUN_0006ce10
FUN_0006ce44
FUN_0006ce84
FUN_0006d018
FUN_0006d214
FUN_0006d254
FUN_000779d0
FUN_000779f0
FUN_0007800c
FUN_000788e0
FUN_00078934
FUN_000789f8
FUN_00078bc8
FUN_00078c4c
FUN_00079270
FUN_000796fc
FUN_00079834
FUN_00079a28
FUN_00079bdc
FUN_00079c5c
FUN_0007a430
FUN_0007a6a0
FUN_0007b0cc
FUN_0007b268
FUN_0007b3bc
FUN_0007b3cc
FUN_0007b67c
FUN_0007b768
FUN_0007bb0c
FUN_0007c008
FUN_0007c034
FUN_0007c078
FUN_0007c088
FUN_0007ca8c
FUN_0007cc2c
FUN_0007cd84
FUN_0007cd94
FUN_0007d044
FUN_0007d130
FUN_0007d558
FUN_0007d9c4
FUN_0007dfe0
FUN_0007e130
FUN_0007e18c
FUN_0007e464
FUN_0007e550
FUN_0007e918
FUN_0007ea54
FUN_0007ec08
FUN_0007ec18
FUN_0007eca8
FUN_0007f39c
FUN_0007f3d0
FUN_0007f400
FUN_0007fd90
FUN_0007ff2c
FUN_00080080
FUN_00080090
FUN_00080340
FUN_0008042c
FUN_000807e0
FUN_00081010
FUN_000811b0
FUN_00081308
FUN_00081318
FUN_000815c8
FUN_000816b4
FUN_00081a60
FUN_00081ea4
FUN_00084778
FUN_00088ac0
FUN_0008a294
FUN_0008a894
FUN_0008aa64
FUN_0008aae8
FUN_0008ac3c
FUN_0008af28
FUN_0008af54
FUN_0008af98
FUN_0008b0a4
FUN_0008b0b4
FUN_0008b18c
FUN_0008b1f0
FUN_0008b8e4
FUN_0008b918
FUN_0008b948
FUN_0008babc
FUN_0008ce40
FUN_0008f70c
FUN_00094f18
FUN_00095104
FUN_00097090
FUN_00097438
FUN_000988ec
FUN_00098a00
FUN_00098bd0
FUN_0009d45c
FUN_0009e964
FUN_000a6174
FUN_000a9828
FUN_000a9848
FUN_000a9f70
FUN_000aa190
FUN_000aa824
FUN_000aa850
FUN_000aa894
FUN_000aa99c
FUN_000aadec
FUN_000ab07c
FUN_000ab0b0
FUN_000ab0e0
FUN_000ab460
FUN_000adb70
FUN_000af3e8
FUN_000af6c0
FUN_000af6e0
FUN_000af740
FUN_000afa6c
FUN_000b0350
FUN_000b07b4
FUN_000b6f04
FUN_000bc5d8
FUN_000c1424
FUN_000c388c
FUN_000c42dc
FUN_000c4fd8
FUN_000c5258
FUN_000c814c
FUN_000ca464
FUN_000ce398
FUN_000cef84
FUN_000cf260
FUN_000cfcc8
FUN_000d2d54
FUN_000d4824
FUN_000d4b48
FUN_000d4c88
FUN_000d5310
FUN_000d5af0
FUN_000e2efc
FUN_000e3b6c
FUN_000e41ac
FUN_000e7118
FUN_000e79a4
FUN_000e7dcc
FUN_000e7dfc
FUN_000e81bc
FUN_000e81e8
FUN_000e822c
FUN_000e82d0
FUN_000e82e0
FUN_000e8370
FUN_000e8a50
FUN_000e8a84
FUN_000e8ab8
FUN_000e8af8
FUN_000e8c6c
FUN_000ec8a8
FUN_000ef4a0
FUN_000ef4ec
FUN_000efee8
FUN_000f2f7c
FUN_000f3078
FUN_000f695c
FUN_000f79c4
FUN_000f7a18
FUN_000f8d04
FUN_00100548
FUN_00113bd0
FUN_00114b0c
FUN_00118a60
FUN_0011a00c
FUN_0011a6d4
FUN_0011ad24
FUN_0011b6d8
FUN_0011c4f8
FUN_0011c9ac
FUN_0011d040
FUN_0011d550
FUN_001201fc
FUN_00121900
FUN_00121940
FUN_00126494
FUN_001264e8
FUN_00126824
FUN_00126878
FUN_001269e0
FUN_00127054
FUN_0012816c
FUN_001282f0
FUN_00129934
FUN_0012a0e4
FUN_0012b4a8
FUN_0012c088
FUN_0012c11c
FUN_0012c160
FUN_0012c770
FUN_0012c938
FUN_0012c968
FUN_0012c99c
FUN_0012c9e0
FUN_0012ca20
FUN_0012cc50
FUN_0012cc60
FUN_0012cd78
FUN_0012e0e8
FUN_0012ed78
FUN_0012f184
FUN_00131294
FUN_001321e4
FUN_00132280
FUN_00137c28
FUN_001380e8
FUN_00138668
FUN_001386ec
FUN_00138e44
FUN_0013921c
FUN_00139248
FUN_0013928c
FUN_001393c0
FUN_0013971c
FUN_00139790
FUN_001397d4
FUN_001397e4
FUN_0013981c
FUN_00139b7c
FUN_00139c74
FUN_0013a364
FUN_0013a398
FUN_0013a3cc
FUN_0013a40c
FUN_0013a5f8
FUN_0013ad2c
FUN_0013ad60
FUN_0013ad90
FUN_0013be98
FUN_0013ce74
FUN_0013e200
FUN_0013e2cc
FUN_0013e48c
FUN_0013f2ec
FUN_00141158
FUN_00141254
FUN_00141574
FUN_00141728
FUN_00141f44
FUN_001423cc
FUN_00142628
FUN_00142778
FUN_00143958
FUN_001443d4
FUN_0014707c
FUN_0014ecc8
FUN_0014eda4
FUN_0014f520
FUN_001502e0
FUN_00150a74
FUN_0015219c
FUN_00152594
FUN_00153128
FUN_00153544
FUN_00153620
FUN_00153718
FUN_00153d24
FUN_001543f0
FUN_00155adc
FUN_00156b20
FUN_00156d9c
FUN_00157574
FUN_001575d0
FUN_001584dc
FUN_00158500
FUN_00158594
FUN_0015a690
FUN_00163034
FUN_0016541c
FUN_001656e0
FUN_00165870
FUN_0016591c
FUN_00165a34
FUN_00165e5c
FUN_00165f98
FUN_0016621c
FUN_00166250
FUN_00166280
FUN_0016653c
FUN_00166964
FUN_00166aac
FUN_00166cf8
FUN_00166d2c
FUN_00166d5c
FUN_001670ec
FUN_00167118
FUN_0016716c
FUN_0016717c
FUN_001673e4
FUN_00167410
FUN_00167464
FUN_00167474
FUN_0016832c
FUN_0016ef78
FUN_0016f114
FUN_0016f268
FUN_0016f278
FUN_0016f528
FUN_0016f614
FUN_0016fb00
FUN_00170a0c
FUN_00171f14
FUN_00173c84
FUN_00173d60
FUN_00177130
FUN_001779f8
FUN_00178274
FUN_00179a48
FUN_0017a2f8
FUN_0017aaa0
FUN_0017fa78
FUN_0017fb98
FUN_00189120
FUN_001919ac
FUN_0019a2e0
FUN_001a305c
FUN_001a30e4
FUN_001a3138
FUN_001a314c
FUN_001a47b4
FUN_001a6724
FUN_001a6858
FUN_001a687c
FUN_001a68c8
FUN_001a68ec
FUN_001a7448
FUN_001a749c
FUN_001a766c
FUN_001a7b88
FUN_001a7c08
FUN_001a83c4
FUN_001a8f80
FUN_001a9b10
FUN_001aa5dc
FUN_001aabfc
FUN_001aac3c
FUN_001aac5c
FUN_001ab068
FUN_001ab41c
FUN_001ab448
FUN_001ab598
FUN_001ab9e8
FUN_001abc64
FUN_001abc98
FUN_001abccc
FUN_001abd0c
FUN_001ae6ec
FUN_001ae9d8
FUN_001aea04
FUN_001aea48
FUN_001aeaec
FUN_001aeafc
FUN_001aec48
FUN_001af358
FUN_001af38c
FUN_001af3bc
FUN_001b2d70
FUN_001b47f8
FUN_001b4838
FUN_001b9720
FUN_001b9924
FUN_001b9af4
FUN_001b9b78
FUN_001b9c8c
FUN_001b9fac
FUN_001b9fd8
FUN_001ba01c
FUN_001ba0c0
FUN_001ba0d0
FUN_001ba140
FUN_001ba1c8
FUN_001ba3b0
FUN_001baa84
FUN_001baab8
FUN_001baae8
FUN_001baf78
FUN_001beb18
FUN_001beb6c
FUN_001bef64
FUN_001bf310
FUN_001bf33c
FUN_001bf3c4
FUN_001bf8f0
FUN_001bfb38
FUN_001bfb6c
FUN_001bfba0
FUN_001bfbe0
FUN_001c0108
FUN_001c0624
FUN_001c06a4
FUN_001c0e60
FUN_001c1d30
FUN_001c21c4
FUN_001c2a3c
FUN_001c3358
FUN_001c3984
FUN_001c6fec
FUN_001c7058
FUN_001cd53c
FUN_001cd5c4
FUN_001cd64c
FUN_001cd68c
FUN_001cda04
FUN_001cda30
FUN_001cda74
FUN_001cdb18
FUN_001cdb28
FUN_001cdbb8
FUN_001ce2c8
FUN_001ce2fc
FUN_001ce32c
FUN_001d46ac
FUN_001d483c
FUN_001d4b74
FUN_001d4d44
FUN_001d4dc8
FUN_001d4edc
FUN_001d4f58
FUN_001d5244
FUN_001d5270
FUN_001d52b4
FUN_001d53c0
FUN_001d53d0
FUN_001d5494
FUN_001d5bc0
FUN_001d5bf4
FUN_001d5c24
FUN_001d5dc8
FUN_001d6b7c
FUN_001d6fd8
FUN_001d7188
FUN_001d7264
FUN_001d75b8
FUN_001d75e4
FUN_001d7628
FUN_001d76cc
FUN_001d76dc
FUN_001d776c
FUN_001d7ed0
FUN_001d7f04
FUN_001d7f38
FUN_001d7f78
FUN_001d8f5c
FUN_001d9830
FUN_001d99e0
FUN_001d9a50
FUN_001d9da4
FUN_001d9dd0
FUN_001d9e14
FUN_001d9e68
FUN_001da550
FUN_001da584
FUN_001da5b8
FUN_001da5f8
FUN_001da76c
FUN_001dab18
FUN_001dbc10
FUN_001dc610
FUN_001e062c
FUN_001e06a8
FUN_001e0f40
FUN_001e1eb8
FUN_001e1ec8
FUN_001e1f80
FUN_001e1fb8
FUN_001e2190
FUN_001e2238
FUN_001e2278
FUN_001e254c
FUN_001e2740
FUN_001e27a4
FUN_001e2e4c
FUN_001e2e80
FUN_001e2eb0
FUN_001e3d44
FUN_001e3dc8
FUN_001e3e50
FUN_001e3e90
FUN_001e41fc
FUN_001e4228
FUN_001e426c
FUN_001e4310
FUN_001e4320
FUN_001e43b0
FUN_001e4aa4
FUN_001e4ad8
FUN_001e4b08
FUN_001e7620
FUN_001e781c
FUN_001e79cc
FUN_001e7a3c
FUN_001e7d18
FUN_001e8220
FUN_001e84f0
FUN_001e8524
FUN_001e8558
FUN_001e8598
FUN_001e872c
FUN_001e8928
FUN_001e8968
FUN_001e9454
FUN_001eb8d4
FUN_001ec974
FUN_001ef330
FUN_001efd50
FUN_001f1568
FUN_001f15b8
FUN_001f1600
FUN_001f1640
FUN_001f4c68
FUN_001f7160
FUN_001f76ac
FUN_001f76cc
FUN_001f770c
FUN_001f8740
FUN_001f8794
FUN_001f88cc
FUN_001f8930
FUN_001f8e6c
FUN_001f8fe0
FUN_001fdacc
FUN_001fdcd0
FUN_001fdd58
FUN_001fe154
FUN_001fe180
FUN_001fe1c4
FUN_001fe1d4
FUN_001fe260
FUN_001fe78c
FUN_001fe81c
FUN_001fea08
FUN_001fea3c
FUN_001fed24
FUN_001fed74
FUN_001ff16c
FUN_001ff658
FUN_00200164
FUN_00201764
FUN_00202c64
FUN_00202cb8
FUN_002030e0
FUN_00203134
FUN_00203410
FUN_002039ac
FUN_00203e9c
FUN_002040b0
FUN_00204234
FUN_002047d0
FUN_00204cc0
FUN_00204ed4
FUN_00204ef4
FUN_002052ec
FUN_00205340
FUN_002054d4
FUN_00205af4
FUN_00206044
FUN_00206258
FUN_00206590
FUN_002084e8
FUN_002087f4
FUN_00208990
FUN_0020cc00
FUN_0020e038
FUN_0020e118
FUN_0020e21c
FUN_0020e26c
FUN_0020e31c
FUN_0020e474
FUN_0020eafc
FUN_0020ebd0
FUN_0020ee0c
FUN_0020ee98
FUN_0020f710
FUN_00211208
FUN_002117a4
FUN_00211f60
FUN_002120e4
FUN_002126a0
FUN_00212bac
FUN_00212dcc
FUN_00216e38
FUN_00217ae0
FUN_00218a9c
FUN_00218af0
FUN_00218f38
FUN_002195b0
FUN_00219748
FUN_0021990c
FUN_00219d88
FUN_00219f14
FUN_0021a070
FUN_0021ae80
FUN_0021aee0
FUN_00223288
FUN_002238b0
FUN_00225e70
FUN_00225ed4
FUN_00225f04
FUN_002262a8
FUN_0022640c
FUN_00226470
FUN_002264a0
FUN_00226774
FUN_00226998
FUN_00226bc0
FUN_00226c04
FUN_00226c34
FUN_00226c74
FUN_00226d60
FUN_00227368
FUN_0022748c
FUN_002276e0
FUN_00227910
FUN_00227954
FUN_00227984
FUN_002279c4
FUN_00227ab0
FUN_00227c18
FUN_00227f7c
FUN_00228878
FUN_00228d24
FUN_00229668
FUN_0022bdb4
FUN_0022c038
FUN_0022c1e8
FUN_0022c26c
FUN_0022c5e4
FUN_0022c610
FUN_0022c654
FUN_0022c664
FUN_0022c71c
FUN_0022c72c
FUN_0022c988
FUN_0022ccb0
FUN_0022cd9c
FUN_0022d474
FUN_0022d4a8
FUN_0022d4d8
FUN_0022daf4
FUN_0022dd58
FUN_0022dd8c
FUN_0022ddbc
FUN_0022e2e8
FUN_00231fc4
FUN_002324c0
FUN_00239258
FUN_00246e14
FUN_0024764c
FUN_00247ec4
FUN_0024c098
FUN_002572cc
FUN_0025a0e8
FUN_0025b8f0
FUN_0025c2c4
FUN_0025c45c
FUN_002661f0
FUN_00266ffc
FUN_00269efc
FUN_00269fb8
FUN_0026a0cc
FUN_0026a138
FUN_0026a168
FUN_0026a240
FUN_0026a2c0
FUN_0026a5f0
FUN_0026a8b8
FUN_0026a98c
FUN_0026ab78
FUN_0026adf8
FUN_0026ae20
FUN_0026b118
FUN_0026b1cc
FUN_0026b33c
FUN_0026b358
FUN_0026b48c
FUN_0026b4b8
FUN_0026b890
FUN_0026b8b4
FUN_0026b974
FUN_0026ba60
FUN_0026c24c
FUN_0026c424
FUN_0026c484
FUN_002709bc
FUN_00270e00
FUN_00270f24
FUN_002711bc
FUN_0027123c
FUN_00271320
FUN_002713a4
FUN_002715a4
FUN_00271668
FUN_00271728
FUN_00271814
FUN_00271a5c
FUN_00271a90
FUN_00271b50
FUN_00271c58
FUN_002721d4
FUN_00280a98
FUN_00280c74
FUN_00280e8c
FUN_00280ff8
FUN_00281158
FUN_002811ac
FUN_002812e4
FUN_00281758
FUN_00281788
FUN_002818d8
FUN_00281a1c
FUN_00281ba8
FUN_00281bc4
FUN_00281cdc
FUN_00281d08
FUN_002820f8
FUN_002821cc
FUN_0028233c
FUN_00282358
FUN_00282470
FUN_00282498
FUN_00282688
FUN_002826a0
FUN_00282b14
FUN_002860e8
FUN_00286270
FUN_002863c4
FUN_00286470
FUN_0028677c
FUN_002867ac
FUN_00286880
FUN_00286a04
FUN_00286a20
FUN_00286b54
FUN_00286b80
FUN_00286d78
FUN_0028d730
FUN_0028d7d8
FUN_0028d938
FUN_0028df90
FUN_0028e04c
FUN_0028e24c
FUN_0028e3a8
FUN_0028e3dc
FUN_0028e5a8
FUN_0028e6b4
FUN_0028e6cc
FUN_0028e710
FUN_0028e7e0
FUN_00290af0
FUN_00290ba0
FUN_00290df4
FUN_00290f78
FUN_0029103c
FUN_00291210
FUN_0029e690
FUN_0029f8fc
FUN_0029f99c
FUN_0029f9b8
FUN_0029fbc4
FUN_0029fc2c
FUN_0029fc40
FUN_0029ffa8
FUN_002a000c
FUN_002a01d0
FUN_002a01e8
FUN_002a0360
FUN_002a037c
FUN_002a0494
FUN_002a04c0
FUN_002a0700
FUN_002a0e90
FUN_002a126c
FUN_002a1284
FUN_002a13f4
FUN_002a1410
FUN_002a1528
FUN_002a1550
FUN_002a19c0
FUN_002a1a98
FUN_002a1ab0
FUN_002a1c20
FUN_002a1c3c
FUN_002a1d54
FUN_002a1d7c
FUN_002a1f58
FUN_002a22a4
FUN_002a92f0
FUN_002aab2c
FUN_002aab7c
FUN_002e98fc
FUN_002ea114
FUN_002eabb4
FUN_002eac9c
FUN_002f3b54
FUN_002f5ab4
FUN_002f6218
FUN_002fb57c
FUN_003004c4
FUN_0031ecb8
FUN_0031ece8
FUN_0031ef74
FUN_0031efa4
FUN_0031f230
FUN_0031f260
FUN_0031f3c8
FUN_0031f430
FUN_0031f4b4
FUN_0031f55c
FUN_0031f658
FUN_0031f6f4
FUN_0031f798
FUN_0031f904
FUN_0031f9a8
FUN_0031faa4
FUN_0031fd8c
FUN_00320064
FUN_00320124
FUN_0032013c
FUN_0032034c
FUN_00320368
FUN_00320480
FUN_003204a8
FUN_0032122c
FUN_003213c0
FUN_003215cc
FUN_0032173c
FUN_00321754
FUN_0032175c
FUN_00321774
FUN_00321820
FUN_003218fc
FUN_0032258c
FUN_00322720
FUN_003228ec
FUN_00322a5c
FUN_00322a74
FUN_00322a7c
FUN_00322a94
FUN_00322b40
FUN_00322c1c
FUN_003238ac
FUN_00323a40
FUN_00323c0c
FUN_00323d7c
FUN_00323d94
FUN_00323d9c
FUN_00323db4
FUN_00323e60
FUN_00323f3c
FUN_00324204
FUN_00325a28
FUN_00325a68
FUN_00325b2c
FUN_00325c00
FUN_00325da8
FUN_00325eac
FUN_00326014
FUN_0032618c
FUN_00326b3c
FUN_00326cc4
FUN_00326e18
FUN_003271a0
FUN_003271d0
FUN_003272a4
FUN_00327428
FUN_00327444
FUN_00327578
FUN_003275a4
FUN_00327ac4
FUN_00327bb0
FUN_00327bc8
FUN_00327d34
FUN_00327d50
FUN_00327e68
FUN_00327e90
FUN_003280c8
FUN_0032829c
FUN_0032ba6c
FUN_00330820
FUN_00330cec
FUN_00335828
FUN_0033783c
FUN_003499a8
FUN_0034ec24
FUN_0035fde4
FUN_00361d94
FUN_0036b534
FUN_0036b89c
FUN_0036b920
FUN_003706d4
FUN_00381b9c
FUN_00381eb0
FUN_003836d4
iostream_385ed0
istream_385e94
operator__385ec4
```

## Build log of this run (build/worklist.log)

```
[19:45:02] build 2026-10-18.1 on /Users/admin/glitchdecomp/fastpass 3/rewrite/pseudocode.c
[19:45:02] Resume check (30173 functions in manifest):
[19:45:02]   the rewrite changed since the last build — updating the split (functions whose code changed get the new code; the others keep their fixes)
[19:45:02]   [redo] split + header: input changed — rebuilding shared.h/globals.cpp and merging with the work already done
[19:45:03]   libclang reported 2 error(s) in the declarations (saved to libclang_parse_errors.txt), e.g.:
[19:45:03]     _parse_monolith.cpp:220: static assertion failed due to requirement 'sizeof(struct section) == 80': Ghidra's size of section
[19:45:03]     _parse_monolith.cpp:236: static assertion failed due to requirement 'sizeof(struct segment_command) == 72': Ghidra's size of segment_command
[19:45:09]   split -> 30173 function TUs, 65 types (+37 forward decls), 30173 prototypes, 0 globals
[19:45:22]     functions: 6031 changed in the rewrite (new code taken), 193 already fixed by the model (kept), 23949 untouched (refreshed with the new split), 0 previously quarantined (restored for another try), 0 not in the old run
[19:45:22]     (the replaced versions are in /Users/admin/glitchdecomp/fastpass 3/snapshots/20261024-194511-build-update)
[19:45:23]   [redo] header check
[19:45:23]   » validate/repair shared headers
[19:45:23]   [redo] compile status
[19:45:23]   » preflight diagnose (surface any systemic cause before spending model time on 30173 functions)
[19:45:24]   preflight: sampled TUs compile — proceeding
[19:45:24]   » isolated compile sweep
[19:45:24]   compiling with 11 parallel worker(s)
[19:47:55]   isolated compile: 30054/30173 TUs pass, 119 need repair (152s)
[19:47:55]   status: 30054 compile, 119 still to fix, 0 quarantined
[19:51:17]   declared 120 name(s) the code uses that Ghidra's pseudocode has too (globals like DAT_..., library functions); compiling the 55 function(s) that use them again
[19:51:17]   compiling with 11 parallel worker(s)
[19:51:17]   isolated compile: 50/55 TUs pass, 5 need repair (1s)
[19:51:18]   LM Studio OK — using the loaded model qwen2.5-coder-3b-instruct-mlx
[19:51:18]   » dependency order + fixer loop
[19:51:18]   callgraph imported: 22076 callers, 64251 edges from callgraph.json
[19:51:18]   callgraph: 582 callee name(s) not in our TU set (external/library calls) — ignored for ordering
[19:51:18]   callgraph: exact deps for 21706/30173 functions
[19:51:19]     FUN_0011d17c -> fixed without the model
[19:51:19]     FUN_00208454 -> fixed without the model
[19:51:19]     FUN_00212fd0 -> fixed without the model
[19:51:19]     FUN_00213f0c -> fixed without the model
[19:51:19]     FUN_0023170c -> fixed without the model
[19:51:19]     FUN_0020cc04 -> fixed without the model
[19:51:19]     FUN_00213b7c -> fixed without the model
[19:51:19]     FUN_00213964 -> fixed without the model
[19:51:19]     FUN_0004b344 -> fixed without the model
[19:51:19]     FUN_001f3cd0 -> fixed without the model
[19:51:19]     FUN_0026ce1c -> fixed without the model
[19:51:19]     FUN_0007ebe0 -> fixed without the model
[19:51:19]     FUN_002135c0 -> fixed without the model
[19:51:19]     FUN_0001b2dc -> fixed without the model
[19:51:19]     FUN_00023d48 -> fixed without the model
[19:51:19]     FUN_001a3a5c -> fixed without the model
[19:51:19]     FUN_00053124 -> fixed without the model
[19:51:19]     FUN_001a9378 -> fixed without the model
[19:51:19]     FUN_0005c368 -> fixed without the model
[19:51:19]     FUN_000305a8 -> fixed without the model
[19:51:19]     FUN_000828e0 -> fixed without the model
[19:51:19]     FUN_000cb488 -> fixed without the model
[19:51:19]     FUN_0010a09c -> fixed without the model
[19:51:19]     FUN_00109dd8 -> fixed without the model
[19:51:19]     FUN_00171a30 -> fixed without the model
[19:51:19]     FUN_000fe7a0 -> fixed without the model
[19:51:19]     FUN_000fddd8 -> fixed without the model
[19:51:19]     FUN_000fe358 -> fixed without the model
[19:51:19]     FUN_001027bc -> fixed without the model
[19:51:19]     FUN_00105064 -> fixed without the model
[19:51:19]     FUN_000feb74 -> fixed without the model
[19:51:19]     FUN_001a374c -> fixed without the model
[19:51:19]     FUN_001084c4 -> fixed without the model
[19:51:19]     FUN_00106410 -> fixed without the model
[19:51:19]     keyEquivalentFromMenuEntry__16b3b0 -> fixed without the model
[19:51:19]     FUN_00109774 -> fixed without the model
[19:51:19]     FUN_001aff18 -> fixed without the model
[19:51:19]     applicationDidBecomeActive_ -> fixed without the model
[19:51:20]     FUN_001a2588 -> fixed without the model
[19:51:20]     insertText__16d864 -> fixed without the model
[19:51:20]     FUN_001723a0 -> fixed without the model
[19:51:20]     close_169730 -> fixed without the model
[19:51:20]     FUN_00270228 -> fixed without the model
[19:51:20]     invalidate_1a8a74 -> fixed without the model
[19:51:20]     FUN_001b8320 -> fixed without the model
[19:51:20]     FUN_003836d4 -> fixed without the model
[19:51:20]     FUN_001b8c8c -> fixed without the model
[19:51:20]     FUN_00173144 -> fixed without the model
[19:51:20]     createLayerTextureWithSize__16cb94 -> fixed without the model
[19:51:20]     updateLayerInRect__16ce54 -> fixed without the model
[19:51:20]     FUN_0028fb48 -> fixed without the model
[19:51:20]     FUN_0032dc78 -> fixed without the model
[19:51:20]     FUN_001725c4 -> fixed without the model
[19:51:20]     FUN_003021b0 -> fixed without the model
[19:51:20]     FUN_002fb554 -> fixed without the model
[19:51:20]     FUN_002fb684 -> fixed without the model
[19:51:20]     FUN_002fa778 -> fixed without the model
[19:51:20]     FUN_0031c93c -> fixed without the model
[19:51:20]     FUN_000349a0 -> fixed without the model
[19:51:20]     FUN_0032ccd4 -> fixed without the model
[19:51:20]     FUN_001728ac -> fixed without the model
[19:51:20]     FUN_0030c560 -> fixed without the model
[19:51:20]     FUN_0030c740 -> fixed without the model
[19:51:20]     FUN_0030f060 -> fixed without the model
[19:51:20]     FUN_0030c890 -> fixed without the model
[19:51:20]     drawRect__16d1bc -> fixed without the model
[19:51:20]     FUN_001a54e0 -> fixed without the model
[19:51:20]   quick fixes (no model): 67 of 69 function(s) compile now
[19:51:20]   fixer loop over 2 failing TU(s), dependency-ordered
[19:51:27]     [2/2] FUN_002a96d8 -> fixed (6s)
[19:51:32]   QUARANTINE FUN_0013ec40: used type 'struct streambuf' where arithmetic or pointer type is required
[19:51:32]     [1/2] FUN_0013ec40 -> quarantined (11s)
[19:51:32]   learned fixes on quarantined functions: 0 of 1 retried compile now
[19:51:32]   learned fixes: 99 proven, 489 being tried, 159 retired (4 new this run); used 74 of 80 time(s) tried, 92% kept; 0 quarantined function(s) rescued. All in build/learned_fixes.txt
[19:51:32]   model: 3 small edit(s) asked for, 0 without a usable edit
[19:51:32]   fixer loop done: 30172 compiling, 1 quarantined
[19:51:32]   why functions are quarantined (most common first; all in fix_report.txt):
[19:51:32]         1 × assigning to 'X' from incompatible type 'X' (aka 'X')  (e.g. FUN_0013ec40)
[19:51:32]   repair loop pass 1 (no model): 0 of 1 rescued
[19:51:40]   QUARANTINE FUN_0013ec40: assigning to 'struct streambuf' from incompatible type 'uint8_t' (aka 'unsigned char')
[19:51:40]   repair loop pass 1 (model): 0 of 1 rescued
[19:51:40]   repair loop pass 2 (no model): 0 of 1 rescued
[19:51:48]   QUARANTINE FUN_0013ec40: used type 'struct streambuf' where arithmetic or pointer type is required
[19:51:48]   repair loop pass 2 (model): 0 of 1 rescued
[19:51:48]   repair loop: 0 quarantined function(s) rescued
[19:53:58]   link round 1: linking 30176 objects ...
[19:54:00]   link round 1: 99 undefined, 0 duplicate symbol(s) — stubbed/quarantined, relinking
[19:54:01]   link round 2: linking 30177 objects ...
[19:54:02]   25 placeholder definition(s) in stubs.cpp (listed in link_report.txt)
[19:54:02]   LINK OK (round 2) -> /Users/admin/glitchdecomp/fastpass 3/build_c/program.dylib
[19:54:23]   final C source: /Users/admin/glitchdecomp/fastpass 3/final/program.c (30172 functions, 17.0 MB), built by final/build.sh into program.dylib
```

## pipeline_state.json

```json
{
  "stages": {
    "export": {
      "done": true,
      "started": "2026-10-24 19:42:07",
      "at": "2026-10-24 19:43:17",
      "seconds": 70,
      "note": "30489/30489 with pseudocode"
    },
    "rewrite": {
      "done": true,
      "started": "2026-10-24 19:43:19",
      "at": "2026-10-24 19:45:02",
      "seconds": 103,
      "model": "",
      "note": "30173/30489 rewritten",
      "model_busy": 12
    },
    "split": {
      "done": true,
      "started": "2026-10-24 19:45:02",
      "at": "2026-10-24 19:47:55",
      "seconds": 174,
      "note": "30054/30173 compile after the sweep"
    },
    "fix": {
      "done": true,
      "started": "2026-10-24 19:47:55",
      "at": "2026-10-24 19:51:48",
      "seconds": 232,
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "model_busy": 11
    },
    "recover": {
      "done": true,
      "started": "2026-10-24 19:51:48",
      "at": "2026-10-24 19:51:48",
      "seconds": 0,
      "model": "qwen2.5-coder-3b-instruct-mlx"
    },
    "privacy": {
      "done": true,
      "started": "2026-10-24 19:43:17",
      "at": "2026-10-24 19:43:19",
      "seconds": 2,
      "note": "1141 replacement(s)"
    },
    "link": {
      "done": true,
      "started": "2026-10-24 19:51:48",
      "at": "2026-10-24 19:54:03",
      "seconds": 134,
      "note": "linked"
    },
    "test": {
      "done": false,
      "started": "2026-10-24 19:54:03",
      "at": "2026-10-24 19:54:09",
      "note": "the rebuilt plugin didn't load: load executable"
    },
    "improve": {
      "done": false,
      "started": "2026-10-24 19:54:09",
      "at": "2026-10-24 19:54:09",
      "note": "off (--improve turns it on)"
    },
    "organize": {
      "done": true,
      "started": "2026-10-24 19:54:09",
      "at": "2026-10-24 19:54:23",
      "note": "final/program.c: 30172 functions",
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "seconds": 13
    }
  },
  "version": "2026-10-25.9",
  "chars_per_token": {
    "ctx": 8192,
    "value": 2.06
  },
  "struggles": [
    {
      "at": "2026-10-24 17:54:17",
      "keys": {
        "rewrite|no usable rewrite: model returned no code (empty reply)": 3,
        "test|the rebuilt plugin didn't load: instantiate (the plugin's factory and constructor run here)": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 18:26:45",
      "keys": {
        "rewrite|no usable rewrite: model returned no code (empty reply)": 3,
        "test|the rebuilt plugin didn't load: load executable": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 18:56:17",
      "keys": {
        "rewrite|no usable rewrite: model returned no code (empty reply)": 3,
        "test|the rebuilt plugin didn't load: load executable": 1,
        "organize|the final C file doesn't build, so final/ wasn't written": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 19:28:19",
      "keys": {
        "test|the rebuilt plugin didn't load: load executable": 1,
        "organize|possible identifying items left (final/ not written)": 275,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 120,
        "fix|fixes that undid each other (the cycle was stopped and the model got the function)": 1,
        "fix|small edits the model couldn't give a usable answer for": 1,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 19:54:23",
      "keys": {
        "fix|quarantined: used type 'X' where arithmetic or pointer type is required": 1,
        "test|the rebuilt plugin didn't load: load executable": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 120,
        "fix|the model repeated an edit that had already failed (skipped)": 2,
        "fix|fixes that undid each other (the cycle was stopped and the model got the function)": 3,
        "link|functions replaced by placeholders to link": 25
      }
    }
  ],
  "rates": [
    {
      "at": "10-24 17:30",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "learned_proven": 96,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 17:54",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 18:26",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "learned_proven": 96,
      "learned_kept_pct": 98.1,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 18:56",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 19:28",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "fix_tried": 1,
      "fix_success_pct": 100.0,
      "fix_per_hour": 23,
      "learned_proven": 97,
      "learned_kept_pct": 98.6,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 19:54",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "fix_tried": 2,
      "fix_success_pct": 50.0,
      "fix_per_hour": 41,
      "learned_proven": 99,
      "learned_kept_pct": 92.5,
      "test_pass_pct": 0.0
    }
  ]
}
```

## report.json

```json
{
  "generated": "2026-10-24 19:54:23",
  "pipeline_version": "2026-10-25.9",
  "workdir": "/Users/admin/glitchdecomp/fastpass 3",
  "export": {
    "functions": 30489,
    "with_pseudocode": 30489,
    "export_version": 2,
    "source": "headless-java",
    "datatypes": 205,
    "signatures": 30489
  },
  "rewrite": {
    "functions": 30489,
    "done": 30489,
    "stale": 12705,
    "skipped": 0,
    "too_big": 0,
    "not_started": 0,
    "renamed": 358,
    "tiny": 13364,
    "in_pieces": 3018,
    "faithful": 0,
    "suspect": 12726,
    "suspect_reasons": {
      "decompiler names left": 9244,
      "no real name": 7099,
      "invented text/printing": 3379,
      "some parts left as Ghidra wrote them": 626,
      "identifying strings left": 444,
      "cut off": 88,
      "raw addresses left": 29
    }
  },
  "build": {
    "functions": 30173,
    "compile": 30172,
    "quarantined": 1,
    "fixed_by_model": 118,
    "rederived": 1,
    "rederived_by": {
      "faithful-pseudocode": 1
    }
  },
  "link": {
    "ok": true,
    "stubs": 20,
    "unresolved": 0
  },
  "improve": {},
  "organize": {
    "note": "final/program.c: 30172 functions",
    "written": true,
    "privacy_hits": 0
  },
  "stages": {
    "export": {
      "done": true,
      "started": "2026-10-24 19:42:07",
      "at": "2026-10-24 19:43:17",
      "seconds": 70,
      "note": "30489/30489 with pseudocode"
    },
    "rewrite": {
      "done": true,
      "started": "2026-10-24 19:43:19",
      "at": "2026-10-24 19:45:02",
      "seconds": 103,
      "model": "",
      "note": "30173/30489 rewritten",
      "model_busy": 12
    },
    "split": {
      "done": true,
      "started": "2026-10-24 19:45:02",
      "at": "2026-10-24 19:47:55",
      "seconds": 174,
      "note": "30054/30173 compile after the sweep"
    },
    "fix": {
      "done": true,
      "started": "2026-10-24 19:47:55",
      "at": "2026-10-24 19:51:48",
      "seconds": 232,
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "model_busy": 11
    },
    "recover": {
      "done": true,
      "started": "2026-10-24 19:51:48",
      "at": "2026-10-24 19:51:48",
      "seconds": 0,
      "model": "qwen2.5-coder-3b-instruct-mlx"
    },
    "privacy": {
      "done": true,
      "started": "2026-10-24 19:43:17",
      "at": "2026-10-24 19:43:19",
      "seconds": 2,
      "note": "1141 replacement(s)"
    },
    "link": {
      "done": true,
      "started": "2026-10-24 19:51:48",
      "at": "2026-10-24 19:54:03",
      "seconds": 134,
      "note": "linked"
    },
    "test": {
      "done": false,
      "started": "2026-10-24 19:54:03",
      "at": "2026-10-24 19:54:09",
      "note": "the rebuilt plugin didn't load: load executable"
    },
    "improve": {
      "done": false,
      "started": "2026-10-24 19:54:09",
      "at": "2026-10-24 19:54:09",
      "note": "off (--improve turns it on)"
    },
    "organize": {
      "done": true,
      "started": "2026-10-24 19:54:09",
      "at": "2026-10-24 19:54:23",
      "note": "final/program.c: 30172 functions",
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "seconds": 13
    }
  }
}
```

## build_state.json

```json
{
  "input_sha": "03c9062fd0adcccf",
  "split_done": true,
  "header_ok": true,
  "sweep_done": true,
  "version": "2026-10-18.1",
  "link_ok": true
}
```
