# Diagnostics — fastpass 3 — 2026-10-24 21:46:28


## Run

```
script: decomp_pipeline 2026-10-25.11 (build 2026-10-18.1)
command: /Users/admin/AIHarness/scripts/decomp_pipeline.py --workdir /Users/admin/glitchdecomp/fastpass 3 --from export --to organize --headless-export --ghidra-home /Users/admin/Downloads/ghidra_12.1.4_PUBLIC --project /Users/admin/glitchpt2.gpr --ctx 8192 --parallel 50 --workers 12 --lang c --no-pseudo --repair-minutes 1 --plugin /Users/admin/Downloads/Glitch_2_1_5_Mac_Free/Glitch2.component
python: 3.15.0 on darwin
compiler: /usr/bin/clang++ (clang)
compile flags: -Wno-c++11-narrowing -arch arm64
--ctx 8192, chars per token 2.06
model: qwen2.5-coder-3b-instruct-mlx
model requests turned down this run: 0, thinking-only answers: 0
fix stage model edits: {'calls': 17, 'no_answer': 0, 'rejected': 0}
```

## What the script struggled with

```

━━━━ what the script struggled with this run ━━━━
(errors it fixed on its own are left out; [also in the last N runs] marks the ones worth changing the script for)
rates (this run last; earlier runs above it):
  run                   compile %      quarantined %             to fix        fixer tried    fixer success %     fixer per hour  recover success %      learned fixes     learned kept %            rescued  ideas adopted/tested        test pass %
  10-24 18:56               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
  10-24 19:28               100.0                0.0                  0                  1              100.0                 23                  -                 97               98.6                  -                     -                0.0
  10-24 19:54               100.0                0.0                  0                  2               50.0                 41                  -                 99               92.5                  -                     -                0.0
  10-24 20:19               100.0                0.0                  0                  3               33.3                 35                  -                104               98.6                  2                     -                0.0
  10-24 21:46               100.0                0.0                  0                 37               97.3                795                  -                122               99.2                  1                   0/1                0.0
couldn't handle:
  test          1 × the rebuilt plugin didn't load: load executable   [also in the last 5 run(s)]
                    → see build/test/test_report.txt
worked around (cost time, nothing lost):
  fix         119 × Ghidra globals / library functions nothing declared (declared once in shared.h)   e.g. LAB_001806a4   [also in the last 5 run(s)]
  fix           2 × fixes that undid each other (the cycle was stopped and the model got the function)   e.g. FUN_001a8494, FUN_0020f76c   [also in the last 3 run(s)]
  link         24 × functions replaced by placeholders to link   [also in the last 5 run(s)]
```

## Log of this run (pipeline.log)

```
[21:32:31] decomp_pipeline 2026-10-25.11: /Users/admin/glitchdecomp/fastpass 3 — stages export → organize
[21:32:31]   --ctx 8192: pieces up to 5303 characters, recover stage up to 11006
[21:32:31] ━━━━ Stage 1/10 · export ━━━━ getting every function's pseudocode from Ghidra (once — after that Ghidra can be closed)
[21:32:31]   using the existing ghidra_export.json (Ghidra not needed)
[21:32:39]   Ghidra lost the return value of 2181 function(s) (226 of them empty: they return what they're given), and 27 read an argument their signature doesn't have: fixing their signatures and decompiling them and their callers again (headless, read-only)
[21:33:21]     ghidra: INFO  GhidraSignatureFix.java>   round 1: 411 function(s) given the parameters they read (GhidraScript)
[21:33:22]     ghidra: INFO  GhidraSignatureFix.java>   round 2: 228 function(s) given the parameters they read (GhidraScript)
[21:33:23]     ghidra: INFO  GhidraSignatureFix.java>   round 3: 24 function(s) given the parameters they read (GhidraScript)
[21:33:23]     ghidra: INFO  GhidraSignatureFix.java>   round 4: 11 function(s) given the parameters they read (GhidraScript)
[21:33:24]     ghidra: INFO  GhidraSignatureFix.java>   round 5: 5 function(s) given the parameters they read (GhidraScript)
[21:33:24]     ghidra: INFO  GhidraSignatureFix.java>   round 6: 5 function(s) given the parameters they read (GhidraScript)
[21:33:25]     ghidra: INFO  GhidraSignatureFix.java>   round 7: 52 function(s) given the parameters they read (GhidraScript)
[21:33:25]     ghidra: INFO  GhidraSignatureFix.java>   round 8: 48 function(s) given the parameters they read (GhidraScript)
[21:33:25]     ghidra: INFO  GhidraSignatureFix.java> parameters found up the call chains: 784; decompiling 7841 function(s) for the export (GhidraScript)
[21:34:01]   signature fix: 2181 function(s) given back their return value, 784 given the parameters they pass on (up the call chains), 7841 decompiled again with them
[21:34:09]   callgraph.json: 22076 functions with internal calls
[21:34:09]   export: 30489/30489 functions have pseudocode, 205 data types, 30489 signatures
[21:34:09] ━━━━ Stage 2/10 · privacy ━━━━ identifying information (names, web and email addresses, bundle IDs, paths, copyright lines) is replaced in Ghidra's export, before anything else sees it; what was replaced is kept in private/ on this Mac only
[21:34:11]   privacy: 1142 replacement(s) in Ghidra's export (6 names, 14 web addresses, 8 copyright lines, 1 email address, 3 user folders, 3 bundle IDs). What was replaced: private/privacy_report.txt (stays on this Mac)
[21:34:11]   privacy: 17 stand-in(s) are values the plugin uses while it runs (bundle ID, web addresses): the rebuilt plugin's Info.plist must use the same ones (listed in private/privacy_report.txt)
[21:34:11] ━━━━ Stage 3/10 · rewrite ━━━━ Ghidra's pseudocode is written out as one C file, with the program's data (no model: the code is what Ghidra decompiled)
[21:34:41]     functions with a system function's name (the system's is used): 3: sync, setbuf, objc_msgSend
[21:34:41]     Ghidra's copies of types the system headers define (the system's are used): 63, e.g. Byte, CGPoint, CGRect, CGSize, FILE, SEL
[21:34:41]     fields Ghidra named that the system's type calls something else (read at their offset): 14
[21:34:45]     pointers only the loader's fix-up list has (no reference in Ghidra): 583, fixed up too
[21:34:45]     static initializers the plugin runs when it loads (as the original does): 91
[21:34:45]     pointers in the data to addresses outside it (not fixed up): 7, listed in rewrite/data_unresolved_pointers.txt
[21:34:45]     data found by its address (not in Ghidra's label list): 496
[21:35:36]     addresses in the data written in the code as numbers ((long *)0x453400): 320, now the rebuilt data's
[21:35:51]     pieces of variables (v._0_8_): 4572
[21:35:51]     16-byte register values (as gh16): 1658
[21:35:51]     C++/Objective-C names in definitions: 1287
[21:35:51]     functions Ghidra said return nothing, whose callers use the result: 863
[21:35:51]     registers Ghidra saw read but nothing gave (as 0): 495
[21:35:51]     C++ qualified names in code: 190
[21:35:51]     types C didn't know (declared opaque): 19
[21:35:51]     types that are also functions (as struct tags): 18
[21:35:51]     switches on a pointer (on its value): 11
[21:35:51]     NAN(x) tests (as isnan): 8
[21:35:51]     of those, returning a stand-in 0 (nothing to return in Ghidra's code): 196, listed in rewrite/lost_returns.txt
[21:35:56]     names that are a type and also a function (the type keeps its struct tag): 12
[21:35:56]   C source from Ghidra's pseudocode: 30173 function(s), 311 library stub(s) called directly, 29 data type(s) with Ghidra's layout, the program's data (35 block(s), 2997 labelled location(s) used, 33768 pointer fix-up(s), 1 placeholder(s) for data outside the export: rewrite/data_placeholders.txt) -> pseudocode.c
[21:35:56] ━━━━ Stage 4/10 · split ━━━━ libclang splits the rewrite into shared.h + one file per function, repairs the header, then compiles every function on its own
[21:39:06] ━━━━ Stage 5/10 · fix ━━━━ functions that don't compile are repaired, callees first: quick deterministic fixes, then the model; what can't be fixed is quarantined
[21:44:05]   fix: 40 model request(s); the model was busy 18% of the stage's 4m
[21:44:05] ━━━━ Stage 6/10 · recover ━━━━ quarantined functions are rebuilt from their Ghidra pseudocode
[21:44:06] ━━━━ Stage 7/10 · link ━━━━ the whole program is compiled and linked; anything still missing gets a placeholder and is listed in link_report.txt
[21:46:09] ━━━━ Stage 8/10 · test ━━━━ the rebuilt plugin and the original (--plugin) render the same test signals in a small test host; their outputs are compared sample by sample
[21:46:15]   test: the rebuilt plugin didn't load: crashed (SIGSEGV) during: load executable
[21:46:15]   test: everything it saw is in /Users/admin/glitchdecomp/fastpass 3/build_c/test/test_report.txt
[21:46:15] ━━━━ Stage 9/10 · improve ━━━━ the code is made easier to read (names, Ghidra's helpers, casts, pointer arithmetic), worst functions first; a change is kept only if the function compiles to the same machine code, so the plugin does exactly what it did
[21:46:15]   improve: off (it's slow, and optional: the final code builds without it). Turn it on with --improve
[21:46:15] ━━━━ Stage 10/10 · organize ━━━━ the whole program is written out as one C source file, final/program.c, with its headers, its data and build.sh; final/ is only replaced once that builds
[21:46:28] ============================================================
[21:46:28] SUMMARY: 30173/30173 functions compile, 0 quarantined, 1 re-derived, link=OK
[21:46:28] Report: /Users/admin/glitchdecomp/fastpass 3/REPORT.md
[21:46:28] 
[21:46:28] ━━━━ what the script struggled with this run ━━━━
[21:46:28] (errors it fixed on its own are left out; [also in the last N runs] marks the ones worth changing the script for)
[21:46:28] rates (this run last; earlier runs above it):
[21:46:28]   run                   compile %      quarantined %             to fix        fixer tried    fixer success %     fixer per hour  recover success %      learned fixes     learned kept %            rescued  ideas adopted/tested        test pass %
[21:46:28]   10-24 18:56               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
[21:46:28]   10-24 19:28               100.0                0.0                  0                  1              100.0                 23                  -                 97               98.6                  -                     -                0.0
[21:46:28]   10-24 19:54               100.0                0.0                  0                  2               50.0                 41                  -                 99               92.5                  -                     -                0.0
[21:46:28]   10-24 20:19               100.0                0.0                  0                  3               33.3                 35                  -                104               98.6                  2                     -                0.0
[21:46:28]   10-24 21:46               100.0                0.0                  0                 37               97.3                795                  -                122               99.2                  1                   0/1                0.0
[21:46:28] couldn't handle:
[21:46:28]   test          1 × the rebuilt plugin didn't load: load executable   [also in the last 5 run(s)]
[21:46:28]                     → see build/test/test_report.txt
[21:46:28] worked around (cost time, nothing lost):
[21:46:28]   fix         119 × Ghidra globals / library functions nothing declared (declared once in shared.h)   e.g. LAB_001806a4   [also in the last 5 run(s)]
[21:46:28]   fix           2 × fixes that undid each other (the cycle was stopped and the model got the function)   e.g. FUN_001a8494, FUN_0020f76c   [also in the last 3 run(s)]
[21:46:28]   link         24 × functions replaced by placeholders to link   [also in the last 5 run(s)]
```

## Build status

```
{
 "functions": 30173,
 "compile": 30173,
 "quarantined": 0,
 "to fix": 0
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
why 0 function(s) are quarantined (first compile error, grouped):
```

## build/link_report.txt

```
stubbed DAT_0042e5a8 (never defined)
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

== proven: 122
[1344 worked, 5 didn't] too few arguments to function call, expected N, have N (part of a line)
    @1();
  → @1(1);
[591 worked, 0 didn't] redefinition of 'X'
    @1 @2 = {0};
  → @2 = (@1){0};
[338 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(@4);
  → @1 = @3(@4);
[298 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1 = @2((@3)@4);
  → @1 = @2((@3)@4, 1);
[243 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2 = {0};
  → @2 = (@1){0};
[235 worked, 53 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
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
[115 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    (@1);
  → (@1, 1);
[112 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → unsigned char @1[16] = {0};@2(@3);
[89 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → *(unsigned char*)&@1 = @2(@3, @4);
[83 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    )@1);
  → )@1, 1);
[82 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16];
[80 worked, 18 didn't] integer constant expression must have integer type, not 'X'
    case"" :
  → case 0 :
[73 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2.@3;
  → @1 = @2[8];
[70 worked, 12 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1*@2;
  → uint64_t @2;
[64 worked, 2 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (void*)@2(
  → @1 = @2(
[57 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    int @1 = {0};
  → @1 = (int){0};
[52 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    double @1 = {0};
  → @1 = (double){0};
[44 worked, 12 didn't] initializing 'X' with an expression of incompatible type 'X' (part of a line)
    @1 = @2(
  → @1 = (unsigned long long)@2(
[43 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2.@3;
  → *(unsigned char*)&@1 = *(unsigned char*)&@2;
[35 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2();
  → (void)@1 = @2();
[34 worked, 1 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    @1 = @2((
  → @1 = ((uint64_t(*)())@2)((
[32 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    float @1 = {0};
  → @1 = (float){0};
[31 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(@2);
  → @1(@2, 1);
[30 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3;
  → @1[8] = @3;
[30 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X') (part of a line)
    @1*@2 = {0
  → @2 = (@1*){0
[30 worked, 0 didn't] expected expression
    return @1 = {0};
  → return @1 = 0;
[29 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 0;
  → @1[8] = 0;
[27 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1, (
  → 0], (
[27 worked, 0 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1(@2
  → ((uint64_t(*)())@1)(@2
[25 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → unsigned char @1[16];@2(@3, @4);
[25 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long @1 = {0};
  → @1 = (long){0};
[25 worked, 6 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2();
  → uint64_t @1 = @2();
[21 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5);
  → unsigned char @1[16] = {0};@2(@3, @4, @5);
[19 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2((long)@3);
  → uintptr_t @1 = @2((long)@3);
[18 worked, 8 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1[0] = @2(
  → unsigned char @1[1] = {0};@2(
[17 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    *@1 =
  → *(uint64_t*)@1 =
[16 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (long)@2(@3, @4);
  → long @1 = @2(@3, @4);
[16 worked, 0 didn't] too few arguments to function call, single argument 'X' was not specified (part of a line)
    @1()
  → ((uint64_t(*)())@1)()
[16 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = @2(@3());
  → @1 = @2(((uint64_t(*)())@3)());
[14 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@1.@3, @4);
  → @1 = @2(*(unsigned int*)&@1, @4);
[14 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16] = {0};@2();
[14 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(@2[0]);
  → @1(@2[0], 1);
[14 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    long*@1 = {0
  → @1 = (long*){0
[12 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned char @1[16] = {0};@2(@3, @4, @5, @6, @7, @8, @9);
[12 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\x01" :
  → case 1 :
[12 worked, 3 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = (*
  → unsigned char @1[16] = {0};(*
[11 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = 0;
  → @1[0] = 0;
[10 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    int @1 = (int)@2(
  → long @1 = @2(
[10 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    *(@1(*)[16])(@2+(long)@3) = @4[0];
  → memcpy(&(*(@1(*)[16])(@2+(long)@3)), &(@4[0]), sizeof(*(@1(*)[16])(@2+(long)@3))<sizeof(@4[0]) ? sizeof(*(@1(*)[16])(@2+(long)@3)) : sizeof(@4[0]));
[10 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[@2
  → ((uint64_t*)(uintptr_t)(@1))[@2
[9 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    , @1.@2, @1.@3, @4.@2, @4.@3, @5.@2,
  → , @1[0], @1[8], @4[0], @4[8], @5[0], @5[8]);
[8 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@3.@4, @3.@5, @6, @7);
  → @1 = @2(@3, @6, @7);
[8 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    long)@1[0x68]+3
  → long)(@1+0x68)+3
[8 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    float*@1 = {0
  → @1 = (float*){0
[7 worked, 0 didn't] variable has incomplete type 'X'
    void std:: @1:: @1(@1*this)
  → void @1(@1*this)
[7 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = @2(@1[0].@3, 1);
  → @1[0] = @2(@1[0], 1);
[7 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\b" :
  → case'\b' :
[7 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    (*@1+
  → (*(uint64_t*)@1+
[7 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[1
  → ((uint64_t*)(uintptr_t)(@1))[1
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
[6 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    void*@1 = {0};
  → @1 = (void*){0};
[6 worked, 0 didn't] expected expression (part of a line)
    @1 = {0};
  → @1 = 0;
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
[5 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\f" :
  → case 0x0C :
[5 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (@2*)@3[1];
  → @1 = *(@2**)(@3+1);
[5 worked, 0 didn't] indirection requires pointer operand ('X' invalid) (part of a line)
    *@1(
  → @1(
[5 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(*(@2*)(@3+0x20));
  → ((uint64_t(*)())@1)(*(@2*)(@3+0x20));
[5 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    *(@1+
  → *(uint64_t*)(@1+
[5 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1(@2, 0, 8, @3());
  → @1(@2, 0, 8, ((uint64_t(*)())@3)());
[5 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X') (part of a line)
    @1 @2 = {0
  → @2 = (@1){0
[5 worked, 1 didn't] member reference base type 'X' is not a structure or union (part of a line)
    @1.@2 = @3
  → @1[1] = @3
[5 worked, 1 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[2
  → ((uint64_t*)(uintptr_t)(@1))[2
[5 worked, 2 didn't] too few arguments to function call, expected N, have N (part of a line)
    (0x3ff0000000000000);
  → (0x3ff0000000000000, 0);
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
[4 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    @1(@2()
  → @1(((uint64_t(*)())@2)()
[4 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    int @1 = {0
  → @1 = (int){0
[4 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    float @1 = {0
  → @1 = (float){0
[4 worked, 1 didn't] used type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (struct @2)@3(
  → @1 = @3(
[4 worked, 1 didn't] used type 'X' (aka 'X') where arithmetic or pointer type is required
    (@1(@2, 3, @3), @3 = = (@4[4])@5(@6, 4, 4))){
  → (@1(@2, 3, @3), @5(@3, 0, 4) = = @5(@6, 4, 4))){
[4 worked, 1 didn't] used type 'X' (aka 'X') where arithmetic or pointer type is required (part of a line)
    ), @1 = = (@2[4])@3(
  → ), @3(@1, 0, 4) = = @3(
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
[3 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (float)powf();
  → @1 = (float)((uint64_t(*)())powf)();
[3 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    *)@1(0x3ff0000000000000
  → *)((uint64_t(*)())@1)(0x3ff0000000000000
[3 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    char*@1 = {0};
  → @1 = (char*){0};
[3 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1;
  → uint64_t @1 = 0;
[3 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1(@2, @3, @4, @5, @6, (long)@7[0], @8)
  → @1((unsigned char*)@2, @3, @4, @5, @6, (long)@7[0], @8);
[3 worked, 1 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = *(long*)((long)&@2.@3+@4);
  → @1 = *(long*)((long)@4[0x6a]+@4);

== candidate: 515
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
[4 worked, 2 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    @1 = @2(@3
  → @1 = ((uint64_t(*)())@2)(@3
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
[2 worked, 0 didn't] too few arguments to function call, single argument 'X' was not specified
    @1();
  → ((uint64_t(*)())@1)();
[2 worked, 0 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1 = @2(@3
  → @1 = ((uint64_t(*)())@2)(@3
[2 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1();
  → ((uint64_t(*)())@1)();
[2 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (long*)@2(0x3ff0000000000000);
  → @1 = (long*)((uint64_t(*)())@2)(0x3ff0000000000000);
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    *(@1(*)[12])((long)@2+0x37c) = @3;
  → memcpy(&(*(@1(*)[12])((long)@2+0x37c)), &(@3), sizeof(*(@1(*)[12])((long)@2+0x37c))<sizeof(@3) ? sizeof(*(@1(*)[12])((long)@2+0x37c)) : sizeof(@3));
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    *(@1(*)[12])((long)@2+0x74) = @3;
  → memcpy(&(*(@1(*)[12])((long)@2+0x74)), &(@3), sizeof(*(@1(*)[12])((long)@2+0x74))<sizeof(@3) ? sizeof(*(@1(*)[12])((long)@2+0x74)) : sizeof(@3));
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = *@2;
  → memcpy(&(@1), &(*@2), sizeof(@1)<sizeof(*@2) ? sizeof(@1) : sizeof(*@2));
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    *(@1(*)[12])(@2+0x71) = @3;
  → memcpy(&(*(@1(*)[12])(@2+0x71)), &(@3), sizeof(*(@1(*)[12])(@2+0x71))<sizeof(@3) ? sizeof(*(@1(*)[12])(@2+0x71)) : sizeof(@3));
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    *(@1(*)[12])(@2+0x73) = @3;
  → memcpy(&(*(@1(*)[12])(@2+0x73)), &(@3), sizeof(*(@1(*)[12])(@2+0x73))<sizeof(@3) ? sizeof(*(@1(*)[12])(@2+0x73)) : sizeof(@3));
[2 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1[3] = (char)(int)(@2*255.0);
  → ((uint8_t*)(uintptr_t)(@1))[3] = (char)(int)(@2*255.0);
[2 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[3
  → ((uint8_t*)(uintptr_t)(@1))[3
[2 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    if((@1)&& (@2 = @3(@4), @2 = = 0)){
  → if((@1)&& (@2 = ((uint64_t(*)())@3)(@4), @2 = = 0)){
[2 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    8, @1()
  → 8, ((uint64_t(*)())@1)()
[2 worked, 0 didn't] redefinition of 'X' (part of a line)
    @1 @2 = {0
  → @2 = (@1){0
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    long @1 = {0
  → @1 = (long){0
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    float*@1 = {0};
  → @1 = (float*){0};
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    char*@1 = {0
  → @1 = (char*){0
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long*@1 = {0};
  → @1 = (long*){0};
[2 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    (*@1!
  → (*(uint64_t*)@1!
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    void*@1 = {0
  → @1 = (void*){0
[2 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1[@2] = *(@3*)((long)@4+10);
  → ((uint64_t*)(uintptr_t)(@1))[@2] = *(@3*)((long)@4+10);
[2 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1[@2+-1] = *(@3*)((long)@4+10);
  → ((uint64_t*)(uintptr_t)(@1))[@2+-1] = *(@3*)((long)@4+10);
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    short*@1 = {0};
  → @1 = (short*){0};
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    short*@1 = {0
  → @1 = (short*){0
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
[2 worked, 1 didn't] too few arguments to function call, expected N, have N (part of a line)
    @1()
  → ((uint64_t(*)())@1)()
[2 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    if(*@1! = 0){
  → if(*(uint64_t*)@1! = 0){
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

== expected expression
   3 idea(s), 0 adopted; parked until something changes (or run 15)
   #200 [no effect] rewrite "*pdVar2 * local_48 + dVar5*dVar4" -> "GH_GETD(*pdVar2 * local_48 + dVar5 * dVar4, 0)"
        its 'before' text isn't in any failing line of the examples
   #201 [repeat] rewrite "*pdVar2 * local_48 + dVar5*dVar4" -> "GH_GETD(*pdVar2 * local_48 + dVar5 * dVar4, 0)"
        same as #200
   #202 [rejected] declare void FUN_002481d8(void *param_1, char ** param_2);
        tested on 20: 0 better, 0 worse, 1 compiling function(s) broke

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
Run test: the rebuilt plugin against the original (2026-10-24 21:46:09)

original: Original.component
  architectures: x86_64, arm64; tested as arm64
rebuilt:  /Users/user?/name1decomp/fastpass 3/build_c/program.dylib (arm64)

packaged the rebuilt program as /Users/user?/name1decomp/fastpass 3/build_c/test/run-oxvnkoxo/Rebuilt.component (deleted after the test), with the original's Info.plist (35 privacy stand-in(s) applied) and its Resources folder linked in

== component Illformed: Name1 (aumf/igl2/DBlu)
factory: original AUPluginFactory; rebuilt AUPluginFactory (as in the original)
rebuilt plugin, loading: FAILED
crashed (SIGSEGV) during: load executable
    CRASH signal=11 (SIGSEGV: bad memory access) address=0x1
    CRASH stack:
    0   aharness_host-arm64-325db53723      0x00000001008152a4 on_crash + 196
    1   libsystem_platform.dylib            0x000000018d081744 _sigtramp + 56
    2   program                             0x00000001068e8e94 FUN_00067718 + 84
    3   program                             0x00000001068e8e30 FUN_000676ec + 32
    4   program                             0x00000001068e8dd0 FUN_00067690 + 56
    5   program                             0x00000001068dd0cc FUN_0005fa70 + 24
    6   program                             0x00000001068ec984 FUN_0006a480 + 32
    7   program                             0x00000001068ec9b0 FUN_0006a4c0 + 12
    8   program                             0x0000000106e937b8 gd_relocate + 1240
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
    25  aharness_host-arm64-325db53723      0x0000000100815628 open_unit + 204
    26  aharness_host-arm64-325db53723      0x00000001008148c8 main + 248
    27  dyld                                0x000000018ccac4e4 start + 6992
    rebuilt functions in the stack (innermost first): FUN_00067718 (funcs/_FUN_00067718.cpp), FUN_000676ec (funcs/_FUN_000676ec.cpp), FUN_00067690 (funcs/_FUN_00067690.cpp), FUN_0005fa70 (funcs/_FUN_0005fa70.cpp), FUN_0006a480 (funcs/_FUN_0006a480.cpp), FUN_0006a4c0 (funcs/_FUN_0006a4c0.cpp)
    (an address near zero: a null pointer, often a global or object the rebuilt program never set up)
    code of FUN_00067718 (funcs/_FUN_00067718.cpp):
         1 | #include "shared.h"
         2 | 
         3 | long FUN_00067718(long param_1,undefined8 param_2)
         4 | {
         5 |   undefined8 uVar1;
         6 |   undefined8 *puVar2;
         7 |   int local_34;
         8 |   undefined8 local_30;
         9 |   long lStack_28;
        10 | 
        11 |   local_30 = param_2;
        12 |   lStack_28 = param_1;
        13 |   FUN_0006777c((undefined8 *)(param_1 + 8));
        14 |   local_34 = 0;
        15 |   FUN_0006779c((long *)(param_1 + 0x10),&local_34);
        16 |   uVar1 = FUN_000677c0();
        17 |   puVar2 = (undefined8*)FUN_000677e8(1);
        18 |   *puVar2 = uVar1;
        19 |   return param_1;
        20 | }
        21 | 
    code of FUN_000676ec (funcs/_FUN_000676ec.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_000676ec(long param_1,undefined8 param_2)
         4 | {
         5 |   FUN_00067718(param_1,param_2);
         6 |   return;
         7 | }
         8 | 
    code of FUN_00067690 (funcs/_FUN_00067690.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_00067690(long param_1)
         4 | {
         5 |   undefined1 auStack_30 [8];
         6 |   long local_28;
         7 | 
         8 |   local_28 = param_1;
         9 |   FUN_000676cc();
        10 |   FUN_000676ec(param_1,auStack_30);
        11 |   return;
        12 | }
        13 | 
    code of FUN_0005fa70 (funcs/_FUN_0005fa70.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0005fa70(long param_1)
         4 | {
         5 |   FUN_00067690(param_1);
         6 |   return;
         7 | }
         8 | 
    code of FUN_0006a480 (funcs/_FUN_0006a480.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0006a480(void)
         4 | {
         5 |   FUN_0005fa70((uintptr_t)(g_block_29 + 0x8));
         6 |   __cxa_atexit(FUN_0005fa90,&GD_DAT_0045e138,0);
         7 |   return;
         8 | }
         9 | 
    code of FUN_0006a4c0 (funcs/_FUN_0006a4c0.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0006a4c0(void)
         4 | {
         5 |   FUN_0006a480();
         6 |   return;
         7 | }
         8 | 
    the rebuilt plugin's load steps (GD_DEBUG):
      data at 0=0x106f64000 1=0x106f65a40 2=0x1072e9860 3=0x1072e9f20 4=0x10730cea0 5=0x107348330 6=0x107367200 7=0x107367340 8=0x107369900 9=0x107369a40 10=0x10736a490 11=0x107382f20 12=0x107383880 13=0x107383af0 14=0x107383dd0 15=0x107383de0 16=0x1073adc70 17=0x1073ae1d0 18=0x1073ae220 19=0x1073ae240 20=0x1073af8a0 21=0x1073b03a0 22=0x1073b1950 23=0x1073b2590 24=0x1073b2730 25=0x1073b2780 26=0x1073b2810 27=0x1073b2820 28=0x1073b2af0 29=0x1073bd9f0 30=0x1073e6d80 31=0x1077f8760 32=0x1077ff360 33=0x1073bf8c0 34=0x107802d90
      fixing up 32214 pointer(s) and 1554 import(s)
      import not found (left null): dyld_stub_binder, at block 12 + 0x268
      fix-ups done; imports not found: 1
      initializer 1/91: FUN_00007144
      initializer 2/91: FUN_0000717c
      initializer 3/91: FUN_00021f34
      initializer 4/91: FUN_00035e5c
      initializer 5/91: FUN_000383cc
      initializer 6/91: FUN_0004530c
      initializer 7/91: FUN_0006a4c0
    registers when it crashed (the ones that point into the rebuilt program explained):
       x0 = 0x0000000000000001  (near zero)
       x1 = 0x000000016f5e946c
       x2 = 0x00000000000120a8
       x3 = 0x000000016f5e900a
       x4 = 0x0000000106eaac37  in the rebuilt program: zoom_ + 0x13d73
       x5 = 0x000000016f5e9540
       x6 = 0x000000000000000a  (near zero)
       x7 = 0x0000000000000000  (zero)
       x8 = 0x0000000000000001  (near zero)
       x9 = 0x0000000000000001  (near zero)
      x10 = 0x0000000000000002  (near zero)
      x11 = 0x00000000fffffffd
      x12 = 0x0000000000000000  (zero)
      x13 = 0x0000000000000000  (zero)
      x14 = 0x0000000000000000  (zero)
      x15 = 0x0000000000000000  (zero)
      x16 = 0x000000018d034618
      x17 = 0x00000001fb0f7228
      x18 = 0x0000000000000000  (zero)
      x19 = 0x000000016f5e9be8
      x20 = 0x0000000106e932e0  in the rebuilt program: gd_relocate + 0x0
      x21 = 0x00000001f9801360
      x22 = 0x0000000106e97d74  in the rebuilt program: zoom_ + 0xeb0
      x23 = 0x000000010685c118
      x24 = 0x0000000000000006  (near zero)
      x25 = 0x00000000000000a0  (near zero)
      x26 = 0x000000010685c248
      x27 = 0x000000010685c0c0
      x28 = 0x0000000000000010  (near zero)
       fp = 0x000000016f5e9490
       lr = 0x00000001068e8e94  in the rebuilt program: FUN_00067718 + 0x54
       sp = 0x000000016f5e9450
       pc = 0x00000001068e8ea0  in the rebuilt program: FUN_00067718 + 0x60
    the rebuilt frames as source lines:
        2: FUN_00067718 (in program.dylib) (_FUN_00067718.cpp:17)
        3: FUN_000676ec (in program.dylib) (_FUN_000676ec.cpp:6)
        4: FUN_00067690 (in program.dylib) (_FUN_00067690.cpp:11)
        5: FUN_0005fa70 (in program.dylib) (_FUN_0005fa70.cpp:6)
        6: FUN_0006a480 (in program.dylib) (_FUN_0006a480.cpp:5)
        7: FUN_0006a4c0 (in program.dylib) (_FUN_0006a4c0.cpp:6)
        8: gd_relocate (in program.dylib) (ghidra_data.c:29976)
       pc: FUN_00067718 (in program.dylib) (_FUN_00067718.cpp:18)
       lr: FUN_00067718 (in program.dylib) (_FUN_00067718.cpp:17)
    where it crashed: FUN_00067718 line 18: *puVar2 = uVar1;
    called just before the crash: FUN_0006779c (funcs/_FUN_0006779c.cpp)
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0006779c(long *param_1,int *param_2)
         4 | {
         5 |   FUN_0006786c(param_1,param_2);
         6 |   return;
         7 | }
         8 | 
    Ghidra's pseudocode of FUN_0006779c:
      void FUN_0006779c(long *param_1,int *param_2)
      
      {
        FUN_0006786c(param_1,param_2);
        return;
      }
    called just before the crash: FUN_000677c0 (funcs/_FUN_000677c0.cpp)
         1 | #include "shared.h"
         2 | 
         3 | undefined8 FUN_000677c0(void)
         4 | {
         5 |   undefined8 uVar1;
         6 | 
         7 |   FUN_000678a4();
         8 |   uVar1 = FUN_001fdacc(1);
         9 |   return uVar1;
        10 | }
        11 | 
    Ghidra's pseudocode of FUN_000677c0:
      undefined8 FUN_000677c0(void)
      
      {
        undefined8 uVar1;
        
        FUN_000678a4();
        uVar1 = FUN_001fdacc();
        return uVar1;
      }
    called just before the crash: FUN_000677e8 (funcs/_FUN_000677e8.cpp)
         1 | #include "shared.h"
         2 | 
         3 | undefined8 FUN_000677e8(undefined8 param_1)
         4 | {
         5 |   return param_1;
         6 | }
         7 | 
    Ghidra's pseudocode of FUN_000677e8:
      undefined8 FUN_000677e8(undefined8 param_1)
      
      {
        return param_1;
      }
    Ghidra's pseudocode of FUN_00067718:
      long FUN_00067718(long param_1,undefined8 param_2)
      
      {
        undefined8 uVar1;
        undefined8 *puVar2;
        int local_34;
        undefined8 local_30;
        long lStack_28;
        
        local_30 = param_2;
        lStack_28 = param_1;
        FUN_0006777c((undefined8 *)(param_1 + 8));
        local_34 = 0;
        FUN_0006779c((long *)(param_1 + 0x10),&local_34);
        uVar1 = FUN_000677c0();
        puVar2 = (undefined8 *)FUN_000677e8();
        *puVar2 = uVar1;
        return param_1;
      }
    Ghidra's pseudocode of FUN_000676ec:
      void FUN_000676ec(long param_1,undefined8 param_2)
      
      {
        FUN_00067718(param_1,param_2);
        return;
      }
    Ghidra's pseudocode of FUN_00067690:
      void FUN_00067690(long param_1)
      
      {
        undefined1 auStack_30 [8];
        long local_28;
        
        local_28 = param_1;
        FUN_000676cc();
        FUN_000676ec(param_1,auStack_30);
        return;
      }
    Ghidra's pseudocode of FUN_0005fa70:
      void FUN_0005fa70(long param_1)
      
      {
        FUN_00067690(param_1);
        return;
      }
    data FUN_0006a480 uses:
      GD_DAT_0045e138: block __bss + 0x8; original 0x45e138, Ghidra's DAT_0045e138; the original has there: 00 00 00 00 00 00 00 00; no fix-up there
      g_block_29 + 0x8 (an address written as a number): original 0x45e138, Ghidra's DAT_0045e138; the original has there: 00 00 00 00 00 00 00 00; no fix-up there
    Ghidra's pseudocode of FUN_0006a480:
      void FUN_0006a480(void)
      
      {
        FUN_0005fa70(0x45e138);
        ___cxa_atexit(FUN_0005fa90,&DAT_0045e138,0);
        return;
      }
    Ghidra's pseudocode of FUN_0006a4c0:
      void FUN_0006a4c0(void)
      
      {
        FUN_0006a480();
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

FUN_000076a4
FUN_0000a9c0
FUN_0000dd2c
FUN_0000f278
FUN_0000f930
FUN_00016738
FUN_000167a4
FUN_0001bcc0
FUN_0001bf00
FUN_00020c08
FUN_00023c5c
FUN_000376e8
FUN_0003cf50
FUN_00042bc8
FUN_00045264
FUN_0004faa0
FUN_00055134
FUN_00059f20
FUN_0005b134
FUN_000613c4
FUN_00068a4c
FUN_000698e0
FUN_0006b48c
FUN_0006bb1c
FUN_0006cbfc
FUN_0006d28c
FUN_00076ce4
FUN_00079bdc
FUN_0007c0c0
FUN_00084778
FUN_00085174
FUN_0008baf4
FUN_0008ce40
FUN_00097090
FUN_00098a00
FUN_00098bd0
FUN_000aadec
FUN_000adb70
FUN_000bc5d8
FUN_000c1424
FUN_000c4fd8
FUN_000ca464
FUN_000cfcc8
FUN_000d4824
FUN_000d4b48
FUN_000d4c88
FUN_000d5310
FUN_000d5af0
FUN_000e17e8
FUN_000e7118
FUN_000e8c6c
FUN_000f695c
FUN_00100548
FUN_00113bd0
FUN_00114b0c
FUN_00119d9c
FUN_00119de4
FUN_0011a00c
FUN_0011a6d4
FUN_0011ad24
FUN_0011b6d8
FUN_0011c4f8
FUN_0011d040
FUN_0011d17c
FUN_0011d550
FUN_001201fc
FUN_00129934
FUN_001321e4
FUN_00132280
FUN_001393f8
FUN_0013982c
FUN_00144490
FUN_0014ed54
FUN_001516bc
FUN_001535d0
FUN_00157574
FUN_001575d0
FUN_00165f98
FUN_00166aac
FUN_001a305c
FUN_001a30e4
FUN_001a314c
FUN_001a6724
FUN_001a6858
FUN_001a687c
FUN_001a68c8
FUN_001a68ec
FUN_001a7b88
FUN_001a8f80
FUN_001ab9e8
FUN_001ba200
FUN_001bf8f0
FUN_001c0624
FUN_001c1d30
FUN_001d5e00
FUN_001da7a4
FUN_001e1fc8
FUN_001e89a0
FUN_001eb8d4
FUN_001efd50
FUN_001effac
FUN_001f8fe0
FUN_001fd9f8
FUN_001fdafc
FUN_001fde4c
FUN_001fe20c
FUN_001fe78c
FUN_002024c8
FUN_002084e8
FUN_0020895c
FUN_0020e344
FUN_0020e370
FUN_0020ebe0
FUN_00219de8
FUN_00223288
FUN_00223db4
FUN_002297e4
FUN_0022c69c
FUN_002324c0
FUN_00234d38
FUN_00235224
FUN_00235ee4
FUN_00239258
FUN_00244530
FUN_002445e0
FUN_0024764c
FUN_002536dc
FUN_0025a0e8
FUN_0025af78
FUN_0025b138
FUN_0025b8f0
FUN_0025c0b4
FUN_0025c2c4
FUN_00265274
FUN_002661f0
FUN_00266ffc
FUN_00269f10
FUN_0026a034
FUN_0026ae50
FUN_0026c438
FUN_00270e14
FUN_002721a8
FUN_002721d4
FUN_00280c88
FUN_00280ec8
FUN_00280f7c
FUN_00281034
FUN_002811e8
FUN_00281338
FUN_0028192c
FUN_00286284
FUN_00286440
FUN_00286db0
FUN_0028e710
FUN_0028e760
FUN_0028e834
FUN_0029fa0c
FUN_0029fbd8
FUN_0029fff4
FUN_002a0a94
FUN_002a0bc8
FUN_002a0e7c
FUN_002a19ac
FUN_002a22a4
FUN_002eac9c
FUN_002f2628
FUN_002f27a8
FUN_002f2974
FUN_002f3e9c
FUN_002f425c
FUN_002f48bc
FUN_002f5ab4
FUN_002f6218
FUN_0030014c
FUN_003004c4
FUN_0031f3dc
FUN_0031fd74
FUN_003213b4
FUN_00322714
FUN_00323a34
FUN_00325b80
FUN_00326cd8
FUN_00326e94
FUN_00327744
FUN_00327ab0
FUN_00328100
FUN_003282d4
FUN_00331c0c
FUN_0035fde4
FUN_00381eb0
FUN_003836d4
exception
istream_385e94
operator__385ec4
runtime_error
streambuf_385ee8
```

## Build log of this run (build/worklist.log)

```
[21:35:56] build 2026-10-18.1 on /Users/admin/glitchdecomp/fastpass 3/rewrite/pseudocode.c
[21:35:56] Resume check (30173 functions in manifest):
[21:35:56]   the rewrite changed since the last build — updating the split (functions whose code changed get the new code; the others keep their fixes)
[21:35:56]   [redo] split + header: input changed — rebuilding shared.h/globals.cpp and merging with the work already done
[21:35:57]   libclang reported 2 error(s) in the declarations (saved to libclang_parse_errors.txt), e.g.:
[21:35:57]     _parse_monolith.cpp:220: static assertion failed due to requirement 'sizeof(struct section) == 80': Ghidra's size of section
[21:35:57]     _parse_monolith.cpp:236: static assertion failed due to requirement 'sizeof(struct segment_command) == 72': Ghidra's size of segment_command
[21:36:04]   split -> 30173 function TUs, 65 types (+37 forward decls), 30173 prototypes, 0 globals
[21:36:19]     functions: 4318 changed in the rewrite (new code taken), 388 already fixed by the model (kept), 25467 untouched (refreshed with the new split), 0 previously quarantined (restored for another try), 0 not in the old run
[21:36:19]     (the replaced versions are in /Users/admin/glitchdecomp/fastpass 3/snapshots/20261024-213606-build-update)
[21:36:20]   [redo] header check
[21:36:20]   » validate/repair shared headers
[21:36:20]   [redo] compile status
[21:36:20]   » preflight diagnose (surface any systemic cause before spending model time on 30173 functions)
[21:36:21]   preflight: sampled TUs compile — proceeding
[21:36:21]   » isolated compile sweep
[21:36:23]   compiling with 11 parallel worker(s)
[21:39:06]   isolated compile: 28984/30173 TUs pass, 1189 need repair (165s)
[21:39:06]   status: 28984 compile, 1189 still to fix, 0 quarantined
[21:42:30]   declared 119 name(s) the code uses that Ghidra's pseudocode has too (globals like DAT_..., library functions); compiling the 54 function(s) that use them again
[21:42:30]   compiling with 11 parallel worker(s)
[21:42:30]   isolated compile: 46/54 TUs pass, 8 need repair (1s)
[21:42:30]   LM Studio OK — using the loaded model qwen2.5-coder-3b-instruct-mlx
[21:42:30]   » dependency order + fixer loop
[21:42:31]   callgraph imported: 22076 callers, 64251 edges from callgraph.json
[21:42:31]   callgraph: 582 callee name(s) not in our TU set (external/library calls) — ignored for ordering
[21:42:31]   callgraph: exact deps for 21706/30173 functions
[21:42:32]     FUN_00216570 -> fixed without the model
[21:42:32]     FUN_001f9ca8 -> fixed without the model
[21:42:32]     FUN_001f9e9c -> fixed without the model
[21:42:32]     FUN_001f9bc4 -> fixed without the model
[21:42:32]     FUN_00206aa0 -> fixed without the model
[21:42:32]     FUN_00225cec -> fixed without the model
[21:42:32]     FUN_00208454 -> fixed without the model
[21:42:32]     FUN_00227920 -> fixed without the model
[21:42:32]     FUN_00226bd0 -> fixed without the model
[21:42:32]     FUN_0020e3d8 -> fixed without the model
[21:42:32]     FUN_0020e018 -> fixed without the model
[21:42:32]     FUN_001f9dec -> fixed without the model
[21:42:32]     FUN_0020e24c -> fixed without the model
[21:42:32]     FUN_00216154 -> fixed without the model
[21:42:32]     FUN_001e21f0 -> fixed without the model
[21:42:32]     FUN_001e1ccc -> fixed without the model
[21:42:32]     FUN_001e2e2c -> fixed without the model
[21:42:32]     FUN_001e2148 -> fixed without the model
[21:42:32]     FUN_001e2e5c -> fixed without the model
[21:42:32]     FUN_001e1c28 -> fixed without the model
[21:42:32]     FUN_001e2e90 -> fixed without the model
[21:42:32]     FUN_0012c098 -> fixed without the model
[21:42:32]     FUN_0012bf08 -> fixed without the model
[21:42:32]     FUN_0012c70c -> fixed without the model
[21:42:32]     FUN_0012c948 -> fixed without the model
[21:42:32]     FUN_0012c978 -> fixed without the model
[21:42:32]     FUN_0012ca00 -> fixed without the model
[21:42:32]     FUN_0022c2ac -> fixed without the model
[21:42:32]     FUN_0022bf54 -> fixed without the model
[21:42:32]     FUN_001e12b4 -> fixed without the model
[21:42:32]     FUN_0022c1a0 -> fixed without the model
[21:42:32]     FUN_0022bd7c -> fixed without the model
[21:42:32]     FUN_0022d454 -> fixed without the model
[21:42:32]     FUN_0022d484 -> fixed without the model
[21:42:32]     FUN_0022d4b8 -> fixed without the model
[21:42:32]     FUN_0022cba8 -> fixed without the model
[21:42:33]     FUN_0022cd10 -> fixed without the model
[21:42:33]     FUN_0022c9fc -> fixed without the model
[21:42:33]     FUN_0012bd48 -> fixed without the model
[21:42:33]     FUN_0022dd38 -> fixed without the model
[21:42:33]     FUN_0022dd68 -> fixed without the model
[21:42:33]     FUN_0022b66c -> fixed without the model
[21:42:33]     FUN_0022bca4 -> fixed without the model
[21:42:33]     FUN_0022d884 -> fixed without the model
[21:42:33]     FUN_0022dd9c -> fixed without the model
[21:42:33]     FUN_0011d17c -> fixed without the model
[21:42:33]     FUN_0022e09c -> fixed without the model
[21:42:33]     FUN_001e2a70 -> fixed without the model
[21:42:33]     FUN_0011b8e8 -> fixed without the model
[21:42:33]     FUN_00055364 -> fixed without the model
[21:42:33]     FUN_0011d040 -> fixed without the model
[21:42:33]     FUN_0012c4c8 -> fixed without the model
[21:42:33]     FUN_001cd26c -> fixed without the model
[21:42:33]     FUN_0022c84c -> fixed without the model
[21:42:33]     FUN_001cd604 -> fixed without the model
[21:42:33]     FUN_001a3234 -> fixed without the model
[21:42:33]     FUN_0022e200 -> fixed without the model
[21:42:33]     FUN_001cd4f4 -> fixed without the model
[21:42:33]     FUN_0022d080 -> fixed without the model
[21:42:33]     FUN_001ce2d8 -> fixed without the model
[21:42:33]     FUN_001ce2a8 -> fixed without the model
[21:42:33]     FUN_001ce30c -> fixed without the model
[21:42:33]     FUN_001e262c -> fixed without the model
[21:42:33]     FUN_001d6ea8 -> fixed without the model
[21:42:33]     FUN_001d72a4 -> fixed without the model
[21:42:33]     FUN_0023170c -> fixed without the model
[21:42:33]     FUN_0022d930 -> fixed without the model
[21:42:33]     FUN_001c7904 -> fixed without the model
[21:42:33]     FUN_00223664 -> fixed without the model
[21:42:33]     FUN_001c4210 -> fixed without the model
[21:42:33]     FUN_0025355c -> fixed without the model
[21:42:33]     FUN_001dd968 -> fixed without the model
[21:42:33]     FUN_001e7a7c -> fixed without the model
[21:42:34]     FUN_001d627c -> fixed without the model
[21:42:34]     FUN_001e7bf0 -> fixed without the model
[21:42:34]     FUN_001cbf5c -> fixed without the model
[21:42:34]     FUN_0020ebb0 -> fixed without the model
[21:42:34]     FUN_00248330 -> fixed without the model
[21:42:34]     FUN_0020ee78 -> fixed without the model
[21:42:34]     FUN_0020ec5c -> fixed without the model
[21:42:34]     FUN_001718c0 -> fixed without the model
[21:42:34]     FUN_001cde94 -> fixed without the model
[21:42:34]     FUN_001ee518 -> fixed without the model
[21:42:34]     FUN_002278f0 -> fixed without the model
[21:42:34]     FUN_002279a4 -> fixed without the model
[21:42:34]     FUN_00227a64 -> fixed without the model
[21:42:34]     FUN_001e5258 -> fixed without the model
[21:42:34]     FUN_001d43ac -> fixed without the model
[21:42:34]     FUN_001d4cfc -> fixed without the model
[21:42:34]     FUN_001d4e08 -> fixed without the model
[21:42:34]     FUN_001d4e50 -> fixed without the model
[21:42:34]     FUN_001e3a74 -> fixed without the model
[21:42:34]     FUN_001e3e08 -> fixed without the model
[21:42:34]     FUN_001e4a84 -> fixed without the model
[21:42:34]     FUN_001e3cfc -> fixed without the model
[21:42:34]     FUN_001e4ab4 -> fixed without the model
[21:42:34]     FUN_001e4ae8 -> fixed without the model
[21:42:34]     FUN_000351d4 -> fixed without the model
[21:42:34]     FUN_001d18b4 -> fixed without the model
[21:42:34]     FUN_001befe0 -> fixed without the model
[21:42:34]     FUN_001bef20 -> fixed without the model
[21:42:34]     FUN_001beccc -> fixed without the model
[21:42:34]     FUN_001d5e8c -> fixed without the model
[21:42:34]     FUN_001edca0 -> fixed without the model
[21:42:34]     FUN_001e37c0 -> fixed without the model
[21:42:34]     FUN_001fde04 -> fixed without the model
[21:42:34]     FUN_001fda2c -> fixed without the model
[21:42:34]     FUN_001fdc8c -> fixed without the model
[21:42:35]     FUN_001bdb68 -> fixed without the model
[21:42:35]     FUN_001fe9e8 -> fixed without the model
[21:42:35]     FUN_001fea18 -> fixed without the model
[21:42:35]     FUN_001bfe24 -> fixed without the model
[21:42:35]     FUN_001bc954 -> fixed without the model
[21:42:35]     FUN_001fed54 -> fixed without the model
[21:42:35]     FUN_001415a4 -> fixed without the model
[21:42:35]     FUN_00141018 -> fixed without the model
[21:42:35]     FUN_0013f8ec -> fixed without the model
[21:42:35]     FUN_001e468c -> fixed without the model
[21:42:35]     FUN_001fac70 -> fixed without the model
[21:42:35]     FUN_00141e8c -> fixed without the model
[21:42:35]     FUN_001442c0 -> fixed without the model
[21:42:35]     FUN_001410a0 -> fixed without the model
[21:42:35]     FUN_001444ec -> fixed without the model
[21:42:35]     FUN_0014edf8 -> fixed without the model
[21:42:35]     FUN_00150058 -> fixed without the model
[21:42:35]     FUN_0014d380 -> fixed without the model
[21:42:35]     FUN_001419b8 -> fixed without the model
[21:42:35]     FUN_0014cf68 -> fixed without the model
[21:42:35]     FUN_0014eebc -> fixed without the model
[21:42:35]     FUN_001680c4 -> fixed without the model
[21:42:35]     FUN_00151ef4 -> fixed without the model
[21:42:35]     FUN_0014eb98 -> fixed without the model
[21:42:35]     FUN_001536dc -> fixed without the model
[21:42:35]     FUN_00153660 -> fixed without the model
[21:42:35]     FUN_0013e2a8 -> fixed without the model
[21:42:35]     FUN_0013e1e0 -> fixed without the model
[21:42:35]     FUN_001fe53c -> fixed without the model
[21:42:35]     FUN_0014f128 -> fixed without the model
[21:42:35]     FUN_001a7a14 -> fixed without the model
[21:42:35]     FUN_001a775c -> fixed without the model
[21:42:35]     FUN_001d4308 -> fixed without the model
[21:42:35]     FUN_001406ec -> fixed without the model
[21:42:35]     FUN_001a752c -> fixed without the model
[21:42:35]     FUN_001a8338 -> fixed without the model
[21:42:36]     FUN_001a75b4 -> fixed without the model
[21:42:36]     FUN_001bfb18 -> fixed without the model
[21:42:36]     FUN_001bfb48 -> fixed without the model
[21:42:36]     FUN_001a7dc0 -> fixed without the model
[21:42:36]     FUN_001c04b0 -> fixed without the model
[21:42:36]     FUN_001a3448 -> fixed without the model
[21:42:36]     FUN_001bfbc0 -> fixed without the model
[21:42:36]     FUN_001c01f8 -> fixed without the model
[21:42:36]     FUN_001bffc8 -> fixed without the model
[21:42:36]     FUN_001201fc -> fixed without the model
[21:42:36]     FUN_001c0050 -> fixed without the model
[21:42:36]     FUN_001c0dd4 -> fixed without the model
[21:42:36]     FUN_0020f008 -> fixed without the model
[21:42:36]     FUN_001a6830 -> fixed without the model
[21:42:36]     FUN_000be0c0 -> fixed without the model
[21:42:36]     FUN_001736b4 -> fixed without the model
[21:42:36]     FUN_001c085c -> fixed without the model
[21:42:36]     FUN_000be83c -> fixed without the model
[21:42:36]     FUN_001a1d80 -> fixed without the model
[21:42:36]     FUN_001e1fec -> fixed without the model
[21:42:36]     FUN_00003a04 -> fixed without the model
[21:42:36]     FUN_001a7370 -> fixed without the model
[21:42:36]     FUN_001bf69c -> fixed without the model
[21:42:36]     FUN_001bea40 -> fixed without the model
[21:42:36]     FUN_000bc2a0 -> fixed without the model
[21:42:36]     FUN_0001ef1c -> fixed without the model
[21:42:36]     FUN_00016b10 -> fixed without the model
[21:42:37]     FUN_000b19f8 -> fixed without the model
[21:42:37]     FUN_00014338 -> fixed without the model
[21:42:37]     FUN_001a314c -> fixed without the model
[21:42:37]     FUN_0003319c -> fixed without the model
[21:42:37]     FUN_000ea8dc -> fixed without the model
[21:42:37]     FUN_000b186c -> fixed without the model
[21:42:37]     FUN_000520e8 -> fixed without the model
[21:42:37]     FUN_002037b8 -> fixed without the model
[21:42:37]     FUN_00203500 -> fixed without the model
[21:42:37]     FUN_002032d0 -> fixed without the model
[21:42:37]     FUN_00173590 -> fixed without the model
[21:42:37]     FUN_00204024 -> fixed without the model
[21:42:37]     FUN_002045dc -> fixed without the model
[21:42:37]     FUN_00204324 -> fixed without the model
[21:42:37]     FUN_002040f4 -> fixed without the model
[21:42:37]     FUN_00203358 -> fixed without the model
[21:42:37]     FUN_0004b344 -> fixed without the model
[21:42:37]     FUN_00204e48 -> fixed without the model
[21:42:37]     FUN_0020417c -> fixed without the model
[21:42:37]     FUN_00065420 -> fixed without the model
[21:42:37]     FUN_000677c0 -> fixed without the model
[21:42:37]     FUN_0006537c -> fixed without the model
[21:42:37]     FUN_00067ad4 -> fixed without the model
[21:42:37]     FUN_00067a14 -> fixed without the model
[21:42:38]     FUN_00068cd4 -> fixed without the model
[21:42:38]     FUN_00068ca4 -> fixed without the model
[21:42:38]     FUN_00068d4c -> fixed without the model
[21:42:38]     FUN_00171a30 -> fixed without the model
[21:42:38]     FUN_000681d4 -> fixed without the model
[21:42:38]     FUN_000682e0 -> fixed without the model
[21:42:38]     FUN_00069a8c -> fixed without the model
[21:42:38]     FUN_0006a280 -> fixed without the model
[21:42:38]     FUN_0006a250 -> fixed without the model
[21:42:38]     FUN_0026ce1c -> fixed without the model
[21:42:38]     FUN_000649ac -> fixed without the model
[21:42:38]     FUN_0006a2b4 -> fixed without the model
[21:42:38]     FUN_0008a070 -> fixed without the model
[21:42:38]     FUN_00089fcc -> fixed without the model
[21:42:38]     FUN_0008ab28 -> fixed without the model
[21:42:38]     FUN_0008aa1c -> fixed without the model
[21:42:38]     FUN_000076a4 -> fixed without the model
[21:42:38]     FUN_0008b100 -> fixed without the model
[21:42:38]     FUN_000687f8 -> fixed without the model
[21:42:38]     FUN_001263a0 -> fixed without the model
[21:42:38]     FUN_002115b0 -> fixed without the model
[21:42:38]     FUN_0012674c -> fixed without the model
[21:42:38]     FUN_002110c8 -> fixed without the model
[21:42:38]     FUN_002112f8 -> fixed without the model
[21:42:38]     FUN_00086ed0 -> fixed without the model
[21:42:38]     FUN_00211ed4 -> fixed without the model
[21:42:38]     FUN_002124a4 -> fixed without the model
[21:42:38]     FUN_00211fa4 -> fixed without the model
[21:42:38]     FUN_00211150 -> fixed without the model
[21:42:38]     FUN_001a2588 -> fixed without the model
[21:42:38]     FUN_002121e8 -> fixed without the model
[21:42:38]     FUN_00069e58 -> fixed without the model
[21:42:39]     FUN_0021195c -> fixed without the model
[21:42:39]     FUN_00212d40 -> fixed without the model
[21:42:39]     FUN_0021202c -> fixed without the model
[21:42:39]     FUN_0022beb0 -> fixed without the model
[21:42:39]     FUN_00206458 -> fixed without the model
[21:42:39]     FUN_00202b8c -> fixed without the model
[21:42:39]     FUN_00218d44 -> fixed without the model
[21:42:39]     FUN_00203008 -> fixed without the model
[21:42:39]     FUN_001a3394 -> fixed without the model
[21:42:39]     FUN_001a374c -> fixed without the model
[21:42:39]     FUN_00219784 -> fixed without the model
[21:42:39]     FUN_00219984 -> fixed without the model
[21:42:39]     FUN_002196bc -> fixed without the model
[21:42:39]     FUN_00201f14 -> fixed without the model
[21:42:39]     FUN_00201d68 -> fixed without the model
[21:42:39]     FUN_0021980c -> fixed without the model
[21:42:39]     FUN_002189c4 -> fixed without the model
[21:42:39]     FUN_00201b2c -> fixed without the model
[21:42:39]     FUN_00201aac -> fixed without the model
[21:42:39]     FUN_00219124 -> fixed without the model
[21:42:39]     FUN_00205900 -> fixed without the model
[21:42:39]     FUN_00205648 -> fixed without the model
[21:42:39]     FUN_00205394 -> fixed without the model
[21:42:39]     FUN_00202220 -> fixed without the model
[21:42:39]     FUN_00202038 -> fixed without the model
[21:42:39]     FUN_002061cc -> fixed without the model
[21:42:39]     FUN_0020541c -> fixed without the model
[21:42:39]     FUN_000a5818 -> fixed without the model
[21:42:39]     FUN_001d7140 -> fixed without the model
[21:42:39]     FUN_001d7eb0 -> fixed without the model
[21:42:39]     FUN_001d7ee0 -> fixed without the model
[21:42:39]     FUN_00201c5c -> fixed without the model
[21:42:39]     FUN_001d7f58 -> fixed without the model
[21:42:39]     FUN_001d9700 -> fixed without the model
[21:42:39]     FUN_001d9a90 -> fixed without the model
[21:42:39]     FUN_001d9998 -> fixed without the model
[21:42:39]     FUN_001da530 -> fixed without the model
[21:42:39]     FUN_00084694 -> fixed without the model
[21:42:39]     FUN_001da560 -> fixed without the model
[21:42:39]     FUN_001f934c -> fixed without the model
[21:42:39]     FUN_001da5d8 -> fixed without the model
[21:42:39]     FUN_000c4d4c -> fixed without the model
[21:42:40]     FUN_002854b0 -> fixed without the model
[21:42:40]     FUN_0012cefc -> fixed without the model
[21:42:40]     FUN_0028611c -> fixed without the model
[21:42:40]     FUN_0012db5c -> fixed without the model
[21:42:40]     FUN_00285690 -> fixed without the model
[21:42:40]     FUN_0028671c -> fixed without the model
[21:42:40]     FUN_00286a08 -> fixed without the model
[21:42:40]     FUN_00286b6c -> fixed without the model
[21:42:40]     FUN_002869f0 -> fixed without the model
[21:42:40]     FUN_0028663c -> fixed without the model
[21:42:40]     FUN_001d7a48 -> fixed without the model
[21:42:40]     FUN_001cd1c8 -> fixed without the model
[21:42:40]     FUN_001d6e04 -> fixed without the model
[21:42:40]     FUN_001d965c -> fixed without the model
[21:42:40]     FUN_00286488 -> fixed without the model
[21:42:40]     FUN_001e39d0 -> fixed without the model
[21:42:40]     FUN_001e7984 -> fixed without the model
[21:42:40]     FUN_001da144 -> fixed without the model
[21:42:40]     FUN_001e7b4c -> fixed without the model
[21:42:40]     FUN_001e84d0 -> fixed without the model
[21:42:40]     FUN_001e8500 -> fixed without the model
[21:42:40]     FUN_00156044 -> fixed without the model
[21:42:40]     FUN_001e8578 -> fixed without the model
[21:42:40]     FUN_001f1ea4 -> fixed without the model
[21:42:40]     FUN_00007d70 -> fixed without the model
[21:42:40]     FUN_000a9cc0 -> fixed without the model
[21:42:40]     FUN_001f1ab4 -> fixed without the model
[21:42:40]     FUN_000a9f2c -> fixed without the model
[21:42:40]     FUN_00008040 -> fixed without the model
[21:42:40]     FUN_000aa040 -> fixed without the model
[21:42:40]     FUN_001cd37c -> fixed without the model
[21:42:40]     FUN_000aa104 -> fixed without the model
[21:42:40]     FUN_00021f4c -> fixed without the model
[21:42:40]     FUN_0000b154 -> fixed without the model
[21:42:40]     FUN_0000def4 -> fixed without the model
[21:42:40]     FUN_001e3b84 -> fixed without the model
[21:42:40]     FUN_0000e054 -> fixed without the model
[21:42:40]     FUN_00012ec0 -> fixed without the model
[21:42:41]     FUN_00011a98 -> fixed without the model
[21:42:41]     FUN_00016c90 -> fixed without the model
[21:42:41]     FUN_00016ce8 -> fixed without the model
[21:42:41]     FUN_00016390 -> fixed without the model
[21:42:41]     FUN_00015dc0 -> fixed without the model
[21:42:41]     FUN_00014e50 -> fixed without the model
[21:42:41]     FUN_000231a4 -> fixed without the model
[21:42:41]     FUN_001e7ff4 -> fixed without the model
[21:42:41]     FUN_000419ec -> fixed without the model
[21:42:41]     FUN_00286574 -> fixed without the model
[21:42:41]     FUN_0001ae70 -> fixed without the model
[21:42:41]     FUN_000231e0 -> fixed without the model
[21:42:41]     FUN_00084778 -> fixed without the model
[21:42:41]     FUN_00027aac -> fixed without the model
[21:42:41]     FUN_00027cac -> fixed without the model
[21:42:41]     FUN_00027d70 -> fixed without the model
[21:42:41]     FUN_00027df8 -> fixed without the model
[21:42:41]     FUN_0001b2dc -> fixed without the model
[21:42:41]     FUN_0002d2a0 -> fixed without the model
[21:42:41]     FUN_000171f8 -> fixed without the model
[21:42:41]     FUN_0002d6bc -> fixed without the model
[21:42:41]     FUN_0002e1dc -> fixed without the model
[21:42:41]     FUN_0003016c -> fixed without the model
[21:42:41]     FUN_0002eae0 -> fixed without the model
[21:42:41]     FUN_00157b54 -> fixed without the model
[21:42:41]     FUN_001654ec -> fixed without the model
[21:42:41]     FUN_00157bac -> fixed without the model
[21:42:41]     FUN_00032c6c -> fixed without the model
[21:42:41]     FUN_001aadd0 -> fixed without the model
[21:42:41]     FUN_001ab0e4 -> fixed without the model
[21:42:41]     FUN_001ab024 -> fixed without the model
[21:42:41]     FUN_001abc44 -> fixed without the model
[21:42:41]     FUN_001abc74 -> fixed without the model
[21:42:41]     FUN_00173144 -> fixed without the model
[21:42:41]     FUN_0003e818 -> fixed without the model
[21:42:41]     FUN_001abcec -> fixed without the model
[21:42:41]     FUN_0003e904 -> fixed without the model
[21:42:41]     FUN_00040414 -> fixed without the model
[21:42:41]     FUN_0016342c -> fixed without the model
[21:42:41]     FUN_000404f0 -> fixed without the model
[21:42:41]     FUN_0004743c -> fixed without the model
[21:42:42]     FUN_00046e1c -> fixed without the model
[21:42:42]     FUN_000471a8 -> fixed without the model
[21:42:42]     FUN_0004301c -> fixed without the model
[21:42:42]     FUN_00048aac -> fixed without the model
[21:42:42]     FUN_000502e0 -> fixed without the model
[21:42:42]     FUN_00051444 -> fixed without the model
[21:42:42]     FUN_000ff0bc -> fixed without the model
[21:42:42]     FUN_001b9564 -> fixed without the model
[21:42:42]     FUN_001b9aac -> fixed without the model
[21:42:42]     FUN_000173a0 -> fixed without the model
[21:42:42]     FUN_0004ab0c -> fixed without the model
[21:42:42]     FUN_001b9bb8 -> fixed without the model
[21:42:42]     FUN_001ab794 -> fixed without the model
[21:42:42]     FUN_000f49a0 -> fixed without the model
[21:42:42]     FUN_000532f4 -> fixed without the model
[21:42:42]     FUN_00053364 -> fixed without the model
[21:42:42]     FUN_001b9c00 -> fixed without the model
[21:42:42]     FUN_001b94c0 -> fixed without the model
[21:42:42]     FUN_000533dc -> fixed without the model
[21:42:42]     FUN_00053af8 -> fixed without the model
[21:42:42]     FUN_0002e28c -> fixed without the model
[21:42:42]     FUN_00053568 -> fixed without the model
[21:42:42]     FUN_00023e68 -> fixed without the model
[21:42:43]     FUN_00053890 -> fixed without the model
[21:42:43]     FUN_00056690 -> fixed without the model
[21:42:43]     FUN_000545e8 -> fixed without the model
[21:42:43]     FUN_00056abc -> fixed without the model
[21:42:43]     FUN_00053124 -> fixed without the model
[21:42:43]     FUN_000548c4 -> fixed without the model
[21:42:43]     FUN_0005beb4 -> fixed without the model
[21:42:43]     FUN_00054330 -> fixed without the model
[21:42:43]     FUN_00067718 -> fixed without the model
[21:42:43]     FUN_0005a2c8 -> fixed without the model
[21:42:43]     FUN_000b9730 -> fixed without the model
[21:42:43]     FUN_00225ea0 -> fixed without the model
[21:42:43]     FUN_00061754 -> fixed without the model
[21:42:43]     closeShellWindow_606b4 -> fixed without the model
[21:42:43]     FUN_001a2e58 -> fixed without the model
[21:42:43]     FUN_0005fcfc -> fixed without the model
[21:42:43]     FUN_0026909c -> fixed without the model
[21:42:43]     FUN_0026b100 -> fixed without the model
[21:42:43]     FUN_00058d7c -> fixed without the model
[21:42:43]     FUN_0026b340 -> fixed without the model
[21:42:43]     FUN_0026b4a4 -> fixed without the model
[21:42:43]     FUN_0026b328 -> fixed without the model
[21:42:43]     FUN_000693ac -> fixed without the model
[21:42:43]     uiViewForAudioUnit_withSize_ -> fixed without the model
[21:42:44]     FUN_0026b020 -> fixed without the model
[21:42:44]     FUN_0026ae54 -> fixed without the model
[21:42:44]     FUN_0026ee0c -> fixed without the model
[21:42:44]     frameTimer_ -> fixed without the model
[21:42:44]     FUN_001a8954 -> fixed without the model
[21:42:44]     FUN_000632ac -> fixed without the model
[21:42:44]     FUN_00065d48 -> fixed without the model
[21:42:44]     FUN_00063be8 -> fixed without the model
[21:42:44]     FUN_000631bc -> fixed without the model
[21:42:44]     FUN_00065e6c -> fixed without the model
[21:42:44]     FUN_000659a0 -> fixed without the model
[21:42:44]     FUN_00065ac8 -> fixed without the model
[21:42:44]     FUN_00065f90 -> fixed without the model
[21:42:44]     FUN_00063504 -> fixed without the model
[21:42:44]     FUN_00066674 -> fixed without the model
[21:42:44]     FUN_000461e4 -> fixed without the model
[21:42:44]     FUN_00066900 -> fixed without the model
[21:42:44]     FUN_000667b4 -> fixed without the model
[21:42:44]     FUN_00066a4c -> fixed without the model
[21:42:44]     FUN_00066b80 -> fixed without the model
[21:42:44]     FUN_00066e14 -> fixed without the model
[21:42:44]     FUN_00066f60 -> fixed without the model
[21:42:44]     FUN_00270228 -> fixed without the model
[21:42:44]     FUN_00066498 -> fixed without the model
[21:42:44]     FUN_00066cb4 -> fixed without the model
[21:42:44]     FUN_002721d4 -> fixed without the model
[21:42:44]     FUN_0006720c -> fixed without the model
[21:42:44]     FUN_00067340 -> fixed without the model
[21:42:44]     FUN_0026af40 -> fixed without the model
[21:42:44]     FUN_00067488 -> fixed without the model
[21:42:44]     FUN_00048c10 -> fixed without the model
[21:42:44]     FUN_00067098 -> fixed without the model
[21:42:44]     FUN_0006aaac -> fixed without the model
[21:42:44]     FUN_0006ad00 -> fixed without the model
[21:42:44]     FUN_0006aa04 -> fixed without the model
[21:42:44]     FUN_0006adc0 -> fixed without the model
[21:42:45]     FUN_0006b67c -> fixed without the model
[21:42:45]     FUN_00066104 -> fixed without the model
[21:42:45]     FUN_0026f624 -> fixed without the model
[21:42:45]     FUN_0006b64c -> fixed without the model
[21:42:45]     FUN_0006b6f4 -> fixed without the model
[21:42:45]     openShellWindow_60180 -> fixed without the model
[21:42:45]     FUN_0006a594 -> fixed without the model
[21:42:45]     FUN_0006c174 -> fixed without the model
[21:42:45]     FUN_0006c470 -> fixed without the model
[21:42:45]     FUN_0006c21c -> fixed without the model
[21:42:45]     FUN_0006c530 -> fixed without the model
[21:42:45]     FUN_0006cdbc -> fixed without the model
[21:42:45]     FUN_0006a6a8 -> fixed without the model
[21:42:45]     FUN_0006cdec -> fixed without the model
[21:42:45]     FUN_0006ce64 -> fixed without the model
[21:42:45]     FUN_0006a894 -> fixed without the model
[21:42:45]     FUN_0006bbdc -> fixed without the model
[21:42:45]     FUN_00076f3c -> fixed without the model
[21:42:45]     FUN_00074d18 -> fixed without the model
[21:42:45]     FUN_00076e98 -> fixed without the model
[21:42:45]     FUN_00086ca4 -> fixed without the model
[21:42:45]     FUN_00078b80 -> fixed without the model
[21:42:45]     FUN_00078c8c -> fixed without the model
[21:42:45]     FUN_000787f0 -> fixed without the model
[21:42:45]     FUN_0006e4c4 -> fixed without the model
[21:42:45]     FUN_0006c008 -> fixed without the model
[21:42:45]     FUN_000791e4 -> fixed without the model
[21:42:45]     FUN_0006b128 -> fixed without the model
[21:42:45]     FUN_0006d34c -> fixed without the model
[21:42:45]     FUN_0007f37c -> fixed without the model
[21:42:45]     FUN_0007f3ac -> fixed without the model
[21:42:45]     FUN_0007f3e0 -> fixed without the model
[21:42:45]     FUN_0007329c -> fixed without the model
[21:42:45]     FUN_0007349c -> fixed without the model
[21:42:45]     FUN_00073600 -> fixed without the model
[21:42:45]     FUN_0006e75c -> fixed without the model
[21:42:45]     FUN_0006f398 -> fixed without the model
[21:42:45]     FUN_0006e5cc -> fixed without the model
[21:42:45]     FUN_0006f784 -> fixed without the model
[21:42:45]     FUN_0006c898 -> fixed without the model
[21:42:45]     FUN_0006f17c -> fixed without the model
[21:42:46]     FUN_00073024 -> fixed without the model
[21:42:46]     FUN_00079a58 -> fixed without the model
[21:42:46]     FUN_0006f350 -> fixed without the model
[21:42:46]     FUN_000793d4 -> fixed without the model
[21:42:46]     FUN_000701d4 -> fixed without the model
[21:42:46]     FUN_0007a5dc -> fixed without the model
[21:42:46]     FUN_0006f3d8 -> fixed without the model
[21:42:46]     FUN_00079554 -> fixed without the model
[21:42:46]     FUN_0007a6cc -> fixed without the model
[21:42:46]     FUN_0007d9a4 -> fixed without the model
[21:42:46]     FUN_00070418 -> fixed without the model
[21:42:46]     FUN_0007e444 -> fixed without the model
[21:42:46]     FUN_00071d64 -> fixed without the model
[21:42:46]     FUN_00071ef0 -> fixed without the model
[21:42:46]     FUN_000702cc -> fixed without the model
[21:42:46]     FUN_0007e504 -> fixed without the model
[21:42:46]     FUN_0007ef84 -> fixed without the model
[21:42:46]     FUN_00071bd0 -> fixed without the model
[21:42:46]     FUN_00073858 -> fixed without the model
[21:42:46]     FUN_00073900 -> fixed without the model
[21:42:46]     FUN_0007371c -> fixed without the model
[21:42:46]     FUN_000727c4 -> fixed without the model
[21:42:46]     FUN_0006dbb8 -> fixed without the model
[21:42:46]     FUN_0007394c -> fixed without the model
[21:42:46]     FUN_00072030 -> fixed without the model
[21:42:46]     FUN_00073b4c -> fixed without the model
[21:42:46]     FUN_00073e7c -> fixed without the model
[21:42:46]     FUN_000721c0 -> fixed without the model
[21:42:46]     FUN_000740a4 -> fixed without the model
[21:42:46]     FUN_00072824 -> fixed without the model
[21:42:46]     FUN_00073bfc -> fixed without the model
[21:42:46]     FUN_00073cb8 -> fixed without the model
[21:42:46]     FUN_00074384 -> fixed without the model
[21:42:46]     FUN_0007468c -> fixed without the model
[21:42:46]     FUN_00074c2c -> fixed without the model
[21:42:46]     FUN_00072a8c -> fixed without the model
[21:42:47]     FUN_00074148 -> fixed without the model
[21:42:47]     FUN_000752c0 -> fixed without the model
[21:42:47]     FUN_00075904 -> fixed without the model
[21:42:47]     FUN_000745dc -> fixed without the model
[21:42:47]     FUN_00073f14 -> fixed without the model
[21:42:47]     FUN_00074244 -> fixed without the model
[21:42:47]     FUN_0007b39c -> fixed without the model
[21:42:47]     FUN_00074fa8 -> fixed without the model
[21:42:47]     FUN_0006fa04 -> fixed without the model
[21:42:47]     FUN_0007b65c -> fixed without the model
[21:42:47]     FUN_00075c7c -> fixed without the model
[21:42:47]     FUN_00075988 -> fixed without the model
[21:42:47]     FUN_0007b71c -> fixed without the model
[21:42:47]     FUN_0007baa4 -> fixed without the model
[21:42:47]     FUN_00075344 -> fixed without the model
[21:42:47]     FUN_0007cd64 -> fixed without the model
[21:42:47]     FUN_0007d024 -> fixed without the model
[21:42:47]     FUN_0007d0e4 -> fixed without the model
[21:42:47]     FUN_0007bac4 -> fixed without the model
[21:42:47]     FUN_0007d470 -> fixed without the model
[21:42:47]     FUN_00080060 -> fixed without the model
[21:42:47]     FUN_0007e88c -> fixed without the model
[21:42:47]     FUN_00080320 -> fixed without the model
[21:42:47]     FUN_000803e0 -> fixed without the model
[21:42:47]     FUN_000807a8 -> fixed without the model
[21:42:47]     FUN_00072390 -> fixed without the model
[21:42:47]     FUN_00080768 -> fixed without the model
[21:42:47]     FUN_000812e8 -> fixed without the model
[21:42:47]     FUN_00081668 -> fixed without the model
[21:42:47]     FUN_000815a8 -> fixed without the model
[21:42:47]     FUN_0008282c -> fixed without the model
[21:42:47]     FUN_00080788 -> fixed without the model
[21:42:47]     FUN_000819f4 -> fixed without the model
[21:42:47]     FUN_00081a14 -> fixed without the model
[21:42:47]     FUN_00088c34 -> fixed without the model
[21:42:47]     FUN_001a987c -> fixed without the model
[21:42:47]     FUN_0008a51c -> fixed without the model
[21:42:47]     FUN_000862a0 -> fixed without the model
[21:42:47]     FUN_0008497c -> fixed without the model
[21:42:47]     FUN_0008656c -> fixed without the model
[21:42:48]     FUN_00087154 -> fixed without the model
[21:42:48]     FUN_00087b58 -> fixed without the model
[21:42:48]     FUN_0008b928 -> fixed without the model
[21:42:48]     FUN_0008b8c4 -> fixed without the model
[21:42:48]     FUN_0008954c -> fixed without the model
[21:42:48]     FUN_0008b8f4 -> fixed without the model
[21:42:48]     FUN_00090ca8 -> fixed without the model
[21:42:48]     FUN_000919c8 -> fixed without the model
[21:42:48]     FUN_0008bea4 -> fixed without the model
[21:42:48]     FUN_000e49e0 -> fixed without the model
[21:42:48]     FUN_00075184 -> fixed without the model
[21:42:48]     FUN_000e4b14 -> fixed without the model
[21:42:48]     FUN_000e7b30 -> fixed without the model
[21:42:48]     FUN_0008fdd0 -> fixed without the model
[21:42:48]     FUN_00087c2c -> fixed without the model
[21:42:48]     FUN_000e7a8c -> fixed without the model
[21:42:48]     FUN_00090680 -> fixed without the model
[21:42:48]     FUN_000e7e3c -> fixed without the model
[21:42:48]     FUN_000e7d84 -> fixed without the model
[21:42:48]     FUN_000e8a30 -> fixed without the model
[21:42:48]     FUN_000e8a60 -> fixed without the model
[21:42:48]     FUN_000e8ad8 -> fixed without the model
[21:42:48]     FUN_0008d320 -> fixed without the model
[21:42:48]     FUN_000ced74 -> fixed without the model
[21:42:48]     FUN_000ce010 -> fixed without the model
[21:42:48]     FUN_0008b4cc -> fixed without the model
[21:42:48]     FUN_00209ca4 -> fixed without the model
[21:42:48]     FUN_00226ba0 -> fixed without the model
[21:42:48]     FUN_000e7784 -> fixed without the model
[21:42:48]     FUN_000cd044 -> fixed without the model
[21:42:48]     FUN_00226c54 -> fixed without the model
[21:42:48]     FUN_00226d14 -> fixed without the model
[21:42:48]     FUN_0009f4b8 -> fixed without the model
[21:42:48]     FUN_0009e570 -> fixed without the model
[21:42:48]     FUN_000a14e8 -> fixed without the model
[21:42:48]     FUN_0009d598 -> fixed without the model
[21:42:48]     FUN_000a0718 -> fixed without the model
[21:42:48]     FUN_000a32dc -> fixed without the model
[21:42:48]     FUN_0009f6fc -> fixed without the model
[21:42:48]     FUN_000a25bc -> fixed without the model
[21:42:48]     FUN_000a5058 -> fixed without the model
[21:42:48]     FUN_000ca214 -> fixed without the model
[21:42:48]     FUN_000a16d4 -> fixed without the model
[21:42:48]     FUN_00227144 -> fixed without the model
[21:42:48]     FUN_000a4338 -> fixed without the model
[21:42:49]     FUN_0009de0c -> fixed without the model
[21:42:49]     FUN_0009ffac -> fixed without the model
[21:42:49]     FUN_000e8654 -> fixed without the model
[21:42:49]     FUN_000a34a8 -> fixed without the model
[21:42:49]     FUN_000a9c18 -> fixed without the model
[21:42:49]     FUN_000ab05c -> fixed without the model
[21:42:49]     FUN_000ab08c -> fixed without the model
[21:42:49]     FUN_000ab0c0 -> fixed without the model
[21:42:49]     FUN_000a6694 -> fixed without the model
[21:42:49]     FUN_000b091c -> fixed without the model
[21:42:49]     FUN_000b0a5c -> fixed without the model
[21:42:49]     FUN_000b09ac -> fixed without the model
[21:42:49]     FUN_000af760 -> fixed without the model
[21:42:49]     FUN_000b1034 -> fixed without the model
[21:42:49]     FUN_000b0498 -> fixed without the model
[21:42:49]     FUN_000ac698 -> fixed without the model
[21:42:49]     FUN_000b278c -> fixed without the model
[21:42:49]     FUN_000b11f8 -> fixed without the model
[21:42:49]     FUN_000b6ee0 -> fixed without the model
[21:42:49]     FUN_00099a34 -> fixed without the model
[21:42:49]     FUN_000b75ec -> fixed without the model
[21:42:49]     FUN_000b6f14 -> fixed without the model
[21:42:49]     FUN_000aab98 -> fixed without the model
[21:42:49]     FUN_000d0430 -> fixed without the model
[21:42:49]     FUN_000bf520 -> fixed without the model
[21:42:49]     FUN_001a43cc -> fixed without the model
[21:42:49]     FUN_000bece4 -> fixed without the model
[21:42:49]     FUN_000c02d4 -> fixed without the model
[21:42:50]     FUN_0015b06c -> fixed without the model
[21:42:50]     FUN_0011e170 -> fixed without the model
[21:42:50]     FUN_0015a2d4 -> fixed without the model
[21:42:50]     FUN_000cb488 -> fixed without the model
[21:42:50]     FUN_000bbafc -> fixed without the model
[21:42:50]     FUN_0011e1f8 -> fixed without the model
[21:42:50]     FUN_000b9510 -> fixed without the model
[21:42:50]     FUN_001592a8 -> fixed without the model
[21:42:50]     FUN_000d373c -> fixed without the model
[21:42:50]     FUN_000d29cc -> fixed without the model
[21:42:50]     FUN_000d0c3c -> fixed without the model
[21:42:50]     FUN_000d19d4 -> fixed without the model
[21:42:50]     FUN_0011a1f8 -> fixed without the model
[21:42:50]     FUN_0009c3ec -> fixed without the model
[21:42:50]     FUN_000cc0bc -> fixed without the model
[21:42:50]     FUN_000d5404 -> fixed without the model
[21:42:50]     FUN_000cb6b0 -> fixed without the model
[21:42:50]     FUN_000ac208 -> fixed without the model
[21:42:50]     FUN_000d56dc -> fixed without the model
[21:42:51]     FUN_000d84c8 -> fixed without the model
[21:42:51]     FUN_000ddcac -> fixed without the model
[21:42:51]     FUN_000de03c -> fixed without the model
[21:42:51]     FUN_000de7e4 -> fixed without the model
[21:42:51]     FUN_000e08f0 -> fixed without the model
[21:42:51]     FUN_000e1d58 -> fixed without the model
[21:42:51]     FUN_000d3ac4 -> fixed without the model
[21:42:51]     FUN_0016579c -> fixed without the model
[21:42:51]     FUN_000e4e8c -> fixed without the model
[21:42:51]     FUN_000e641c -> fixed without the model
[21:42:51]     FUN_000eb738 -> fixed without the model
[21:42:51]     FUN_000ea3dc -> fixed without the model
[21:42:51]     FUN_0016374c -> fixed without the model
[21:42:51]     FUN_000f235c -> fixed without the model
[21:42:51]     FUN_00101df8 -> fixed without the model
[21:42:51]     FUN_000af418 -> fixed without the model
[21:42:51]     FUN_00109dd8 -> fixed without the model
[21:42:51]     FUN_0010a09c -> fixed without the model
[21:42:51]     FUN_000fdd50 -> fixed without the model
[21:42:52]     FUN_000feb20 -> fixed without the model
[21:42:52]     FUN_000f660c -> fixed without the model
[21:42:52]     FUN_000e02e8 -> fixed without the model
[21:42:52]     FUN_000e6a1c -> fixed without the model
[21:42:52]     FUN_000d4114 -> fixed without the model
[21:42:52]     FUN_00101194 -> fixed without the model
[21:42:52]     FUN_00100548 -> fixed without the model
[21:42:52]     FUN_00101468 -> fixed without the model
[21:42:52]     FUN_00100dec -> fixed without the model
[21:42:52]     FUN_00101b18 -> fixed without the model
[21:42:52]     FUN_00101574 -> fixed without the model
[21:42:52]     FUN_00101778 -> fixed without the model
[21:42:52]     FUN_00101c5c -> fixed without the model
[21:42:52]     FUN_00101d90 -> fixed without the model
[21:42:52]     FUN_00101ccc -> fixed without the model
[21:42:52]     FUN_00101ec8 -> fixed without the model
[21:42:52]     FUN_000fe7a0 -> fixed without the model
[21:42:52]     FUN_00101e60 -> fixed without the model
[21:42:52]     FUN_00101f38 -> fixed without the model
[21:42:52]     FUN_00102098 -> fixed without the model
[21:42:52]     FUN_00102034 -> fixed without the model
[21:42:52]     FUN_00102184 -> fixed without the model
[21:42:52]     FUN_000fe358 -> fixed without the model
[21:42:52]     FUN_00102120 -> fixed without the model
[21:42:52]     FUN_000d44e8 -> fixed without the model
[21:42:52]     FUN_00105064 -> fixed without the model
[21:42:52]     FUN_000feb74 -> fixed without the model
[21:42:52]     FUN_001027bc -> fixed without the model
[21:42:52]     FUN_00102f48 -> fixed without the model
[21:42:52]     FUN_00102698 -> fixed without the model
[21:42:53]     FUN_00105d54 -> fixed without the model
[21:42:53]     FUN_0010568c -> fixed without the model
[21:42:53]     FUN_00105884 -> fixed without the model
[21:42:53]     FUN_00105a7c -> fixed without the model
[21:42:53]     FUN_00105f4c -> fixed without the model
[21:42:53]     FUN_00106144 -> fixed without the model
[21:42:53]     FUN_00103704 -> fixed without the model
[21:42:53]     FUN_0010234c -> fixed without the model
[21:42:53]     FUN_0010834c -> fixed without the model
[21:42:53]     FUN_001f53e0 -> fixed without the model
[21:42:53]     FUN_00108250 -> fixed without the model
[21:42:53]     FUN_00107e94 -> fixed without the model
[21:42:53]     FUN_00108a68 -> fixed without the model
[21:42:53]     FUN_00108c1c -> fixed without the model
[21:42:53]     FUN_001090f0 -> fixed without the model
[21:42:53]     FUN_0010a4b0 -> fixed without the model
[21:42:53]     FUN_000fddd8 -> fixed without the model
[21:42:53]     FUN_001120e4 -> fixed without the model
[21:42:53]     FUN_0011547c -> fixed without the model
[21:42:53]     FUN_0010f14c -> fixed without the model
[21:42:53]     FUN_001161d0 -> fixed without the model
[21:42:53]     FUN_00120e44 -> fixed without the model
[21:42:53]     FUN_00109774 -> fixed without the model
[21:42:53]     FUN_000b7074 -> fixed without the model
[21:42:53]     FUN_001279b8 -> fixed without the model
[21:42:54]     FUN_00119aac -> fixed without the model
[21:42:54]     FUN_001282ac -> fixed without the model
[21:42:54]     FUN_00125aa4 -> fixed without the model
[21:42:54]     FUN_00106410 -> fixed without the model
[21:42:54]     FUN_001297c0 -> fixed without the model
[21:42:54]     FUN_00115b30 -> fixed without the model
[21:42:54]     FUN_0012f044 -> fixed without the model
[21:42:54]     FUN_0013838c -> fixed without the model
[21:42:54]     FUN_001382e8 -> fixed without the model
[21:42:54]     FUN_0012f164 -> fixed without the model
[21:42:54]     FUN_001a305c -> fixed without the model
[21:42:54]     FUN_00132824 -> fixed without the model
[21:42:54]     FUN_001084c4 -> fixed without the model
[21:42:54]     FUN_000e0ec0 -> fixed without the model
[21:42:54]     FUN_00131d50 -> fixed without the model
[21:42:54]     FUN_0013972c -> fixed without the model
[21:42:54]     FUN_00139b34 -> fixed without the model
[21:42:54]     FUN_00138620 -> fixed without the model
[21:42:54]     FUN_0013872c -> fixed without the model
[21:42:54]     FUN_0013805c -> fixed without the model
[21:42:54]     FUN_0013a344 -> fixed without the model
[21:42:54]     FUN_0013a374 -> fixed without the model
[21:42:54]     FUN_0013a3ec -> fixed without the model
[21:42:54]     FUN_001398c4 -> fixed without the model
[21:42:54]     FUN_0013ad0c -> fixed without the model
[21:42:54]     FUN_001377ac -> fixed without the model
[21:42:54]     FUN_0013ad3c -> fixed without the model
[21:42:54]     FUN_0013785c -> fixed without the model
[21:42:54]     FUN_00117bd8 -> fixed without the model
[21:42:54]     FUN_00137f60 -> fixed without the model
[21:42:54]     FUN_00132b4c -> fixed without the model
[21:42:54]     FUN_001aff18 -> fixed without the model
[21:42:54]     FUN_0013ad70 -> fixed without the model
[21:42:54]     FUN_00154694 -> fixed without the model
[21:42:55]     FUN_00155cdc -> fixed without the model
[21:42:55]     FUN_00155e84 -> fixed without the model
[21:42:55]     FUN_00164f38 -> fixed without the model
[21:42:55]     FUN_00164e90 -> fixed without the model
[21:42:55]     FUN_0016516c -> fixed without the model
[21:42:55]     FUN_001650c4 -> fixed without the model
[21:42:55]     FUN_001653d8 -> fixed without the model
[21:42:55]     FUN_001657e4 -> fixed without the model
[21:42:55]     FUN_0016569c -> fixed without the model
[21:42:55]     FUN_00139f50 -> fixed without the model
[21:42:55]     FUN_00165890 -> fixed without the model
[21:42:55]     FUN_001661fc -> fixed without the model
[21:42:55]     FUN_0016622c -> fixed without the model
[21:42:55]     FUN_00166260 -> fixed without the model
[21:42:55]     FUN_0013a8dc -> fixed without the model
[21:42:55]     FUN_00166cd8 -> fixed without the model
[21:42:55]     FUN_00166d08 -> fixed without the model
[21:42:55]     FUN_00166d3c -> fixed without the model
[21:42:55]     FUN_00164cf4 -> fixed without the model
[21:42:55]     FUN_00164dc4 -> fixed without the model
[21:42:55]     FUN_00155b50 -> fixed without the model
[21:42:55]     FUN_00134180 -> fixed without the model
[21:42:55]     mainLoop_ -> fixed without the model
[21:42:55]     FUN_00135198 -> fixed without the model
[21:42:55]     worksWhenModal -> fixed without the model
[21:42:55]     becomeKeyWindow_169ddc -> fixed without the model
[21:42:55]     setFrame_display__169580 -> fixed without the model
[21:42:55]     canBecomeKeyWindow_169d4c -> fixed without the model
[21:42:55]     setStyleMask__169384 -> fixed without the model
[21:42:56]     canBecomeMainWindow -> fixed without the model
[21:42:56]     resignKeyWindow_169f10 -> fixed without the model
[21:42:56]     FUN_00165c30 -> fixed without the model
[21:42:56]     FUN_00123e8c -> fixed without the model
[21:42:56]     FUN_00166738 -> fixed without the model
[21:42:56]     applicationDidUnhide_ -> fixed without the model
[21:42:56]     screenParameterChanged_ -> fixed without the model
[21:42:56]     windowWillMiniaturize_ -> fixed without the model
[21:42:56]     applicationDidHide_ -> fixed without the model
[21:42:56]     windowDidMove_ -> fixed without the model
[21:42:56]     applicationDidResignActive_ -> fixed without the model
[21:42:56]     deminiaturize__16a920 -> fixed without the model
[21:42:56]     miniaturize__16a88c -> fixed without the model
[21:42:56]     windowDidDeminiaturize_ -> fixed without the model
[21:42:56]     zoom__16a9c8 -> fixed without the model
[21:42:56]     performClose__16aa5c -> fixed without the model
[21:42:56]     closeButtonProxi_ -> fixed without the model
[21:42:56]     toggleFullScreen_ -> fixed without the model
[21:42:56]     windowBecameKeyOrMainWindow_ -> fixed without the model
[21:42:56]     FUN_00171bd4 -> fixed without the model
[21:42:56]     performKeyEquivalent_ -> fixed without the model
[21:42:56]     menuCallback_ -> fixed without the model
[21:42:57]     openAbout_ -> fixed without the model
[21:42:57]     openPreferences_ -> fixed without the model
[21:42:57]     makeBackingLayer_16c910 -> fixed without the model
[21:42:57]     prepareForDragOperation_ -> fixed without the model
[21:42:57]     sendEvent__16adcc -> fixed without the model
[21:42:57]     draggingEntered_ -> fixed without the model
[21:42:57]     performDragOperation_ -> fixed without the model
[21:42:57]     createMetalLayer_16c9d0 -> fixed without the model
[21:42:57]     applicationDidBecomeActive_ -> fixed without the model
[21:42:57]     markedRange -> fixed without the model
[21:42:57]     doCommandBySelector_ -> fixed without the model
[21:42:57]     FUN_0016f248 -> fixed without the model
[21:42:57]     keyboardInputSourceChanged_ -> fixed without the model
[21:42:57]     FUN_0016f508 -> fixed without the model
[21:42:57]     FUN_0016f5c8 -> fixed without the model
[21:42:57]     FUN_0016f95c -> fixed without the model
[21:42:57]     FUN_0017036c -> fixed without the model
[21:42:58]     FUN_001709c8 -> fixed without the model
[21:42:58]     FUN_001739d0 -> fixed without the model
[21:42:58]     FUN_0017392c -> fixed without the model
[21:42:58]     FUN_00173c3c -> fixed without the model
[21:42:58]     FUN_00173da0 -> fixed without the model
[21:42:58]     close_169730 -> fixed without the model
[21:42:58]     initWithContentRect_styleMask_backing_defer__168d74 -> fixed without the model
[21:42:58]     FUN_00178314 -> fixed without the model
[21:42:58]     setMarkedText_selectedRange_ -> fixed without the model
[21:42:58]     firstRectForCharacterRange_ -> fixed without the model
[21:42:58]     FUN_00187d88 -> fixed without the model
[21:42:58]     FUN_00190614 -> fixed without the model
[21:42:58]     FUN_00198f50 -> fixed without the model
[21:42:58]     layout_1a88bc -> fixed without the model
[21:42:58]     FUN_003836d4 -> fixed without the model
[21:42:59]     invalidate_1a8a74 -> fixed without the model
[21:42:59]     FUN_00215ea0 -> fixed without the model
[21:42:59]     viewDidMoveToWindow_1a8cf8 -> fixed without the model
[21:42:59]     viewDidUnhide_1a90dc -> fixed without the model
[21:42:59]     viewDidHide_1a8e8c -> fixed without the model
[21:42:59]     viewWillMoveToSuperview__1a8b48 -> fixed without the model
[21:42:59]     idleTimer_ -> fixed without the model
[21:42:59]     FUN_001aad28 -> fixed without the model
[21:42:59]     FUN_001ae660 -> fixed without the model
[21:42:59]     updateLayerInRect__16ce54 -> fixed without the model
[21:42:59]     viewFrameChanged_ -> fixed without the model
[21:42:59]     FUN_001af338 -> fixed without the model
[21:42:59]     FUN_001ac418 -> fixed without the model
[21:42:59]     FUN_001af368 -> fixed without the model
[21:42:59]     FUN_0027f4a0 -> fixed without the model
[21:42:59]     FUN_001ae170 -> fixed without the model
[21:42:59]     createLayerTextureWithSize__16cb94 -> fixed without the model
[21:42:59]     FUN_001af39c -> fixed without the model
[21:43:00]     FUN_0027f524 -> fixed without the model
[21:43:00]     FUN_00280b20 -> fixed without the model
[21:43:00]     FUN_00281380 -> fixed without the model
[21:43:00]     FUN_002816f8 -> fixed without the model
[21:43:00]     FUN_00280a84 -> fixed without the model
[21:43:00]     FUN_00281bac -> fixed without the model
[21:43:00]     FUN_00281890 -> fixed without the model
[21:43:00]     FUN_0028112c -> fixed without the model
[21:43:00]     FUN_00281cf4 -> fixed without the model
[21:43:00]     FUN_001728ac -> fixed without the model
[21:43:00]     FUN_00281b94 -> fixed without the model
[21:43:00]     FUN_00281618 -> fixed without the model
[21:43:00]     FUN_0028206c -> fixed without the model
[21:43:00]     FUN_0028144c -> fixed without the model
[21:43:00]     FUN_001aef24 -> fixed without the model
[21:43:00]     FUN_00282340 -> fixed without the model
[21:43:00]     FUN_001722dc -> fixed without the model
[21:43:00]     FUN_00282484 -> fixed without the model
[21:43:00]     FUN_00282328 -> fixed without the model
[21:43:00]     FUN_001a3fa8 -> fixed without the model
[21:43:00]     FUN_00281f8c -> fixed without the model
[21:43:00]     FUN_002807ac -> fixed without the model
[21:43:00]     FUN_00282930 -> fixed without the model
[21:43:00]     FUN_00282a58 -> fixed without the model
[21:43:00]     FUN_00281dd8 -> fixed without the model
[21:43:00]     FUN_00326b70 -> fixed without the model
[21:43:00]     FUN_00327140 -> fixed without the model
[21:43:00]     FUN_0032742c -> fixed without the model
[21:43:00]     FUN_00327590 -> fixed without the model
[21:43:01]     FUN_00327414 -> fixed without the model
[21:43:01]     FUN_001725c4 -> fixed without the model
[21:43:01]     FUN_00327060 -> fixed without the model
[21:43:01]     FUN_00327658 -> fixed without the model
[21:43:01]     FUN_00327a08 -> fixed without the model
[21:43:01]     FUN_00327d38 -> fixed without the model
[21:43:01]     FUN_00326eac -> fixed without the model
[21:43:01]     FUN_00327e7c -> fixed without the model
[21:43:01]     FUN_00327d20 -> fixed without the model
[21:43:01]     FUN_0032790c -> fixed without the model
[21:43:01]     FUN_00326aec -> fixed without the model
[21:43:01]     FUN_001afa08 -> fixed without the model
[21:43:01]     FUN_002eabb4 -> fixed without the model
[21:43:01]     FUN_002f9180 -> fixed without the model
[21:43:01]     FUN_00327758 -> fixed without the model
[21:43:01]     FUN_00281538 -> fixed without the model
[21:43:01]     FUN_001b35d4 -> fixed without the model
[21:43:01]     FUN_00281ec4 -> fixed without the model
[21:43:01]     FUN_001b7894 -> fixed without the model
[21:43:01]     FUN_001b7ba8 -> fixed without the model
[21:43:01]     FUN_001ba28c -> fixed without the model
[21:43:01]     FUN_001baa64 -> fixed without the model
[21:43:01]     drawRect__16d1bc -> fixed without the model
[21:43:01]     FUN_001baac8 -> fixed without the model
[21:43:01]     FUN_001b8320 -> fixed without the model
[21:43:01]     FUN_001b8c8c -> fixed without the model
[21:43:01]     FUN_001baa94 -> fixed without the model
[21:43:01]     FUN_00326f98 -> fixed without the model
[21:43:01]     FUN_001bec24 -> fixed without the model
[21:43:01]     FUN_001bb79c -> fixed without the model
[21:43:01]     FUN_001c1dd8 -> fixed without the model
[21:43:02]     FUN_001c1ef0 -> fixed without the model
[21:43:02]     FUN_001c3870 -> fixed without the model
[21:43:02]     FUN_001c1e00 -> fixed without the model
[21:43:02]     FUN_00327844 -> fixed without the model
[21:43:02]     FUN_001b0ad0 -> fixed without the model
[21:43:02]     FUN_001c6818 -> fixed without the model
[21:43:02]     FUN_001c6d78 -> fixed without the model
[21:43:02]     FUN_001dd434 -> fixed without the model
[21:43:02]     FUN_001ba68c -> fixed without the model
[21:43:02]     FUN_001ca15c -> fixed without the model
[21:43:02]     FUN_001d5ba0 -> fixed without the model
[21:43:02]     FUN_001d5bd0 -> fixed without the model
[21:43:02]     FUN_001d5c04 -> fixed without the model
[21:43:02]     FUN_001ca5b8 -> fixed without the model
[21:43:02]     FUN_001dd708 -> fixed without the model
[21:43:02]     FUN_001d94f4 -> fixed without the model
[21:43:02]     FUN_001cab68 -> fixed without the model
[21:43:02]     FUN_001e034c -> fixed without the model
[21:43:02]     FUN_001d1544 -> fixed without the model
[21:43:02]     FUN_001ebd10 -> fixed without the model
[21:43:02]     FUN_0025a3b4 -> fixed without the model
[21:43:02]     FUN_00255938 -> fixed without the model
[21:43:02]     FUN_002558dc -> fixed without the model
[21:43:02]     FUN_001f7f0c -> fixed without the model
[21:43:02]     FUN_001e0d4c -> fixed without the model
[21:43:02]     FUN_001f88dc -> fixed without the model
[21:43:02]     FUN_001d5770 -> fixed without the model
[21:43:02]     FUN_001ad0a4 -> fixed without the model
[21:43:02]     FUN_002051fc -> fixed without the model
[21:43:02]     FUN_00217c64 -> fixed without the model
[21:43:02]     FUN_001e0798 -> fixed without the model
[21:43:02]     FUN_00206430 -> fixed without the model
[21:43:02]     FUN_001df4a8 -> fixed without the model
[21:43:03]     FUN_001dfc68 -> fixed without the model
[21:43:03]     FUN_002260dc -> fixed without the model
[21:43:03]     FUN_00216c18 -> fixed without the model
[21:43:03]     FUN_002265a8 -> fixed without the model
[21:43:03]     FUN_00227f38 -> fixed without the model
[21:43:03]     FUN_0022643c -> fixed without the model
[21:43:03]     FUN_00228374 -> fixed without the model
[21:43:03]     FUN_00229698 -> fixed without the model
[21:43:03]     FUN_0022b1ac -> fixed without the model
[21:43:03]     FUN_0022ac20 -> fixed without the model
[21:43:03]     FUN_00253b2c -> fixed without the model
[21:43:03]     FUN_00272dcc -> fixed without the model
[21:43:03]     FUN_00277880 -> fixed without the model
[21:43:03]     FUN_00270cac -> fixed without the model
[21:43:03]     FUN_0027b1d8 -> fixed without the model
[21:43:03]     FUN_00282b28 -> fixed without the model
[21:43:03]     FUN_00280990 -> fixed without the model
[21:43:03]     FUN_0024798c -> fixed without the model
[21:43:03]     FUN_0028e6b8 -> fixed without the model
[21:43:03]     FUN_0028f894 -> fixed without the model
[21:43:03]     FUN_002722a0 -> fixed without the model
[21:43:03]     FUN_0028e6a0 -> fixed without the model
[21:43:03]     FUN_0028ad60 -> fixed without the model
[21:43:03]     FUN_00325a54 -> fixed without the model
[21:43:03]     FUN_00325a14 -> fixed without the model
[21:43:03]     FUN_00325b14 -> fixed without the model
[21:43:03]     FUN_0031f2ac -> fixed without the model
[21:43:03]     FUN_00320350 -> fixed without the model
[21:43:03]     FUN_0032004c -> fixed without the model
[21:43:03]     FUN_00320494 -> fixed without the model
[21:43:03]     FUN_00320338 -> fixed without the model
[21:43:03]     FUN_00320b04 -> fixed without the model
[21:43:03]     FUN_0031ff68 -> fixed without the model
[21:43:03]     FUN_00320928 -> fixed without the model
[21:43:03]     FUN_00320d00 -> fixed without the model
[21:43:03]     FUN_00321728 -> fixed without the model
[21:43:03]     FUN_00321740 -> fixed without the model
[21:43:03]     FUN_0031fdb4 -> fixed without the model
[21:43:04]     FUN_003205e8 -> fixed without the model
[21:43:04]     FUN_00320ed0 -> fixed without the model
[21:43:04]     FUN_00321c9c -> fixed without the model
[21:43:04]     FUN_003217e8 -> fixed without the model
[21:43:04]     FUN_00321e78 -> fixed without the model
[21:43:04]     FUN_00322060 -> fixed without the model
[21:43:04]     FUN_00322a48 -> fixed without the model
[21:43:04]     FUN_00322a60 -> fixed without the model
[21:43:04]     FUN_0032195c -> fixed without the model
[21:43:04]     FUN_00322230 -> fixed without the model
[21:43:04]     FUN_00322fbc -> fixed without the model
[21:43:04]     FUN_00323380 -> fixed without the model
[21:43:04]     FUN_00323198 -> fixed without the model
[21:43:04]     FUN_00322b08 -> fixed without the model
[21:43:04]     FUN_00323d68 -> fixed without the model
[21:43:04]     FUN_00323d80 -> fixed without the model
[21:43:04]     FUN_00323e28 -> fixed without the model
[21:43:04]     FUN_00323550 -> fixed without the model
[21:43:04]     FUN_002cb60c -> fixed without the model
[21:43:04]     FUN_002d2030 -> fixed without the model
[21:43:04]     FUN_00322c7c -> fixed without the model
[21:43:04]     FUN_002d0088 -> fixed without the model
[21:43:04]     FUN_002e853c -> fixed without the model
[21:43:04]     FUN_002cc1d0 -> fixed without the model
[21:43:04]     FUN_002cc784 -> fixed without the model
[21:43:04]     FUN_002cdff0 -> fixed without the model
[21:43:04]     FUN_0032dc78 -> fixed without the model
[21:43:04]     FUN_00277d6c -> fixed without the model
[21:43:04]     FUN_00299f84 -> fixed without the model
[21:43:04]     FUN_002fb554 -> fixed without the model
[21:43:04]     FUN_002fe4a0 -> fixed without the model
[21:43:04]     FUN_0029f8e8 -> fixed without the model
[21:43:04]     FUN_0029f988 -> fixed without the model
[21:43:04]     FUN_0029f9a0 -> fixed without the model
[21:43:04]     FUN_0029fa70 -> fixed without the model
[21:43:04]     FUN_0029ff48 -> fixed without the model
[21:43:04]     FUN_002a0364 -> fixed without the model
[21:43:04]     FUN_0032ccd4 -> fixed without the model
[21:43:04]     FUN_002a034c -> fixed without the model
[21:43:04]     FUN_002a04ac -> fixed without the model
[21:43:04]     FUN_0029fe4c -> fixed without the model
[21:43:04]     FUN_0031fea0 -> fixed without the model
[21:43:04]     FUN_002a09a8 -> fixed without the model
[21:43:04]     FUN_002a0adc -> fixed without the model
[21:43:05]     FUN_002a118c -> fixed without the model
[21:43:05]     FUN_002a13f8 -> fixed without the model
[21:43:05]     FUN_0029fc5c -> fixed without the model
[21:43:05]     FUN_002a153c -> fixed without the model
[21:43:05]     FUN_002a13e0 -> fixed without the model
[21:43:05]     FUN_002a10a8 -> fixed without the model
[21:43:05]     FUN_002a1904 -> fixed without the model
[21:43:05]     FUN_002a06ac -> fixed without the model
[21:43:05]     FUN_002a1c24 -> fixed without the model
[21:43:05]     FUN_002a1d68 -> fixed without the model
[21:43:05]     FUN_002a1c0c -> fixed without the model
[21:43:05]     FUN_002a0ef4 -> fixed without the model
[21:43:05]     FUN_002a96d8 -> fixed without the model
[21:43:05]     FUN_002a1808 -> fixed without the model
[21:43:05]     FUN_002ccef8 -> fixed without the model
[21:43:05]     FUN_002cd094 -> fixed without the model
[21:43:05]     FUN_002cf3b8 -> fixed without the model
[21:43:05]     FUN_002d4c34 -> fixed without the model
[21:43:05]     FUN_002a1654 -> fixed without the model
[21:43:05]     FUN_002ce5f8 -> fixed without the model
[21:43:05]     FUN_002d5934 -> fixed without the model
[21:43:05]     FUN_002d5a24 -> fixed without the model
[21:43:05]     FUN_003020bc -> fixed without the model
[21:43:05]     FUN_002d4d24 -> fixed without the model
[21:43:05]     FUN_00302264 -> fixed without the model
[21:43:05]     FUN_002a1ef0 -> fixed without the model
[21:43:05]     FUN_00303ab8 -> fixed without the model
[21:43:05]     FUN_00304acc -> fixed without the model
[21:43:05]     FUN_003040e4 -> fixed without the model
[21:43:05]     FUN_00303980 -> fixed without the model
[21:43:05]     FUN_0030cc98 -> fixed without the model
[21:43:05]     FUN_0030f060 -> fixed without the model
[21:43:05]     FUN_0029fd6c -> fixed without the model
[21:43:05]     FUN_0030cad0 -> fixed without the model
[21:43:05]     FUN_0030f444 -> fixed without the model
[21:43:05]     FUN_0030cbd0 -> fixed without the model
[21:43:06]     FUN_0030fbc0 -> fixed without the model
[21:43:06]     FUN_0030fdf8 -> fixed without the model
[21:43:06]     FUN_003101d0 -> fixed without the model
[21:43:06]     FUN_0030c890 -> fixed without the model
[21:43:06]     FUN_0030ffb8 -> fixed without the model
[21:43:06]     FUN_002a0fe0 -> fixed without the model
[21:43:06]     FUN_0030fafc -> fixed without the model
[21:43:06]     FUN_00310308 -> fixed without the model
[21:43:06]     FUN_00310e30 -> fixed without the model
[21:43:06]     FUN_0030c740 -> fixed without the model
[21:43:06]     FUN_00311108 -> fixed without the model
[21:43:06]     FUN_00311574 -> fixed without the model
[21:43:06]     FUN_00310908 -> fixed without the model
[21:43:06]     FUN_00310a38 -> fixed without the model
[21:43:06]     FUN_002a1740 -> fixed without the model
[21:43:06]     FUN_0030c560 -> fixed without the model
[21:43:06]     FUN_003196d0 -> fixed without the model
[21:43:06]     FUN_00315a54 -> fixed without the model
[21:43:06]     FUN_00311a68 -> fixed without the model
[21:43:06]     FUN_00315e9c -> fixed without the model
[21:43:06]     FUN_00316d9c -> fixed without the model
[21:43:06]     FUN_00312228 -> fixed without the model
[21:43:06]     FUN_00312658 -> fixed without the model
[21:43:06]     FUN_00316f00 -> fixed without the model
[21:43:06]     FUN_00311980 -> fixed without the model
[21:43:06]     FUN_00317020 -> fixed without the model
[21:43:06]     FUN_003177a4 -> fixed without the model
[21:43:06]     FUN_0031980c -> fixed without the model
[21:43:06]     FUN_0031a0b0 -> fixed without the model
[21:43:06]     FUN_00315dfc -> fixed without the model
[21:43:06]     FUN_00311890 -> fixed without the model
[21:43:06]     FUN_0031a8fc -> fixed without the model
[21:43:06]     FUN_003197ac -> fixed without the model
[21:43:06]     FUN_0031a040 -> fixed without the model
[21:43:06]     FUN_0031b77c -> fixed without the model
[21:43:06]     FUN_0031d494 -> fixed without the model
[21:43:06]     FUN_0031a884 -> fixed without the model
[21:43:06]     FUN_0031d52c -> fixed without the model
[21:43:06]     FUN_0031b738 -> fixed without the model
[21:43:06]     FUN_00349a38 -> fixed without the model
[21:43:06]     FUN_0031c07c -> fixed without the model
[21:43:06]     FUN_00315d38 -> fixed without the model
[21:43:06]     FUN_00326800 -> fixed without the model
[21:43:06]     FUN_0031d248 -> fixed without the model
[21:43:06]     FUN_0031b70c -> fixed without the model
[21:43:06]     FUN_00354168 -> fixed without the model
[21:43:07]   quick fixes (no model): 1106 of 1143 function(s) compile now
[21:43:07]   ideas (before the one-by-one fixes): 1 kind(s) of error that 8 or more functions share get ideas from the model
[21:43:22]   ideas: 4 asked, 1 tested, 0 adopted, 2 repeats caught, 0 function(s) compile now. All in build/ideas.txt
[21:43:22]   fixer loop over 37 failing TU(s), dependency-ordered
[21:43:41]     [7/37] FUN_00219b04 -> fixed (18s)
[21:43:42]     [2/37] FUN_00248060 -> fixed (19s)
[21:43:42]     [14/37] FUN_00220ed0 -> fixed (0s)
[21:43:42]     [15/37] FUN_001a54e0 -> fixed (0s)
[21:43:45]     [1/37] FUN_00253668 -> fixed (22s)
[21:43:45]     [17/37] FUN_00326994 -> fixed (0s)
[21:43:45]     [18/37] FUN_00255658 -> fixed (0s)
[21:43:46]     [12/37] FUN_0026f294 -> fixed (23s)
[21:43:46]     [20/37] FUN_0027ca0c -> fixed (0s)
[21:43:46]     [21/37] FUN_002875f8 -> fixed (0s)
[21:43:46]     [22/37] FUN_00287b88 -> fixed (0s)
[21:43:46]     [23/37] FUN_00287f18 -> fixed (0s)
[21:43:46]     [24/37] FUN_0028fcd4 -> fixed (0s)
[21:43:46]     [25/37] FUN_0029133c -> fixed (0s)
[21:43:46]     [26/37] FUN_0031e640 -> fixed (0s)
[21:43:46]     [27/37] FUN_002ca1dc -> fixed (0s)
[21:43:46]     [28/37] FUN_002c9b94 -> fixed (0s)
[21:43:46]     [29/37] FUN_002cbf10 -> fixed (0s)
[21:43:46]     [30/37] FUN_0029a1f0 -> fixed (0s)
[21:43:47]     [31/37] FUN_002d1688 -> fixed (0s)
[21:43:47]     [32/37] FUN_002d101c -> fixed (0s)
[21:43:47]     [33/37] FUN_0030798c -> fixed (0s)
[21:43:47]     [34/37] FUN_0034fb38 -> fixed (0s)
[21:43:47]     [35/37] FUN_0035ecc4 -> fixed (0s)
[21:43:47]     [36/37] FUN_0036df48 -> fixed (0s)
[21:43:47]     [8/37] FUN_0000cbac -> fixed (24s)
[21:43:47]     [37/37] FUN_003709f8 -> fixed (0s)
[21:43:48]     [4/37] FUN_00223948 -> fixed (25s)
[21:43:49]     [10/37] FUN_00030924 -> fixed (26s)
[21:43:50]     [6/37] FUN_001c0f60 -> fixed (27s)
[21:43:52]     [9/37] FUN_00220afc -> fixed (30s)
[21:43:55]     [11/37] FUN_00268dcc -> fixed (32s)
[21:44:00]   QUARANTINE FUN_001a8494: expected expression
[21:44:00]     [5/37] FUN_001a8494 -> quarantined (37s)
[21:44:01]     [13/37] FUN_000cab20 -> fixed (20s)
[21:44:03]     [16/37] insertText__16d864 -> fixed (20s)
[21:44:04]     [19/37] FUN_0025d944 -> fixed (19s)
[21:44:05]     [3/37] FUN_0020f76c -> fixed (42s)
[21:44:05]     FUN_001a8494 -> fixed after quarantine (learned fix)
[21:44:05]   learned fixes on quarantined functions: 1 of 1 retried compile now
[21:44:05]   learned fixes: 122 proven, 515 being tried, 159 retired (41 new this run); used 2111 of 2128 time(s) tried, 99% kept; 1 quarantined function(s) rescued. All in build/learned_fixes.txt
[21:44:05]   model: 17 small edit(s) asked for, 0 without a usable edit
[21:44:05]   fixer loop done: 30173 compiling, 0 quarantined
[21:44:05]   repair loop: 0 quarantined function(s) rescued
[21:46:04]   link round 1: linking 30176 objects ...
[21:46:06]   link round 1: 98 undefined, 0 duplicate symbol(s) — stubbed/quarantined, relinking
[21:46:07]   link round 2: linking 30177 objects ...
[21:46:08]   24 placeholder definition(s) in stubs.cpp (listed in link_report.txt)
[21:46:08]   LINK OK (round 2) -> /Users/admin/glitchdecomp/fastpass 3/build_c/program.dylib
[21:46:28]   previous final/ moved to /Users/admin/glitchdecomp/fastpass 3/snapshots/20261024-214628-final
[21:46:28]   final C source: /Users/admin/glitchdecomp/fastpass 3/final/program.c (30173 functions, 17.2 MB), built by final/build.sh into program.dylib
```

## pipeline_state.json

```json
{
  "stages": {
    "export": {
      "done": true,
      "started": "2026-10-24 21:32:31",
      "at": "2026-10-24 21:34:09",
      "seconds": 98,
      "note": "30489/30489 with pseudocode"
    },
    "rewrite": {
      "done": true,
      "started": "2026-10-24 21:34:11",
      "at": "2026-10-24 21:35:56",
      "seconds": 105,
      "model": "",
      "note": "30173/30489 rewritten",
      "model_busy": 12
    },
    "split": {
      "done": true,
      "started": "2026-10-24 21:35:56",
      "at": "2026-10-24 21:39:06",
      "seconds": 190,
      "note": "28984/30173 compile after the sweep"
    },
    "fix": {
      "done": true,
      "started": "2026-10-24 21:39:06",
      "at": "2026-10-24 21:44:05",
      "seconds": 299,
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "model_busy": 18
    },
    "recover": {
      "done": true,
      "started": "2026-10-24 21:44:05",
      "at": "2026-10-24 21:44:06",
      "seconds": 0,
      "model": "qwen2.5-coder-3b-instruct-mlx"
    },
    "privacy": {
      "done": true,
      "started": "2026-10-24 21:34:09",
      "at": "2026-10-24 21:34:11",
      "seconds": 2,
      "note": "1142 replacement(s)"
    },
    "link": {
      "done": true,
      "started": "2026-10-24 21:44:06",
      "at": "2026-10-24 21:46:09",
      "seconds": 123,
      "note": "linked"
    },
    "test": {
      "done": false,
      "started": "2026-10-24 21:46:09",
      "at": "2026-10-24 21:46:15",
      "note": "the rebuilt plugin didn't load: load executable"
    },
    "improve": {
      "done": false,
      "started": "2026-10-24 21:46:15",
      "at": "2026-10-24 21:46:15",
      "note": "off (--improve turns it on)"
    },
    "organize": {
      "done": true,
      "started": "2026-10-24 21:46:15",
      "at": "2026-10-24 21:46:28",
      "note": "final/program.c: 30173 functions",
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "seconds": 13
    }
  },
  "version": "2026-10-25.11",
  "chars_per_token": {
    "ctx": 8192,
    "value": 2.06
  },
  "struggles": [
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
    },
    {
      "at": "2026-10-24 20:19:43",
      "keys": {
        "test|the rebuilt plugin didn't load: load executable": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "fix|fixes that undid each other (the cycle was stopped and the model got the function)": 4,
        "fix|the model repeated an edit that had already failed (skipped)": 3,
        "fix|small edits the model couldn't give a usable answer for": 2,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 21:46:28",
      "keys": {
        "test|the rebuilt plugin didn't load: load executable": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "fix|fixes that undid each other (the cycle was stopped and the model got the function)": 2,
        "link|functions replaced by placeholders to link": 24
      }
    }
  ],
  "rates": [
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
    },
    {
      "at": "10-24 20:19",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "fix_tried": 3,
      "fix_success_pct": 33.3,
      "fix_per_hour": 35,
      "learned_proven": 104,
      "learned_kept_pct": 98.6,
      "rescued": 2,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 21:46",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "fix_tried": 37,
      "fix_success_pct": 97.3,
      "fix_per_hour": 795,
      "learned_proven": 122,
      "learned_kept_pct": 99.2,
      "rescued": 1,
      "ideas_adopted": "0/1",
      "test_pass_pct": 0.0
    }
  ]
}
```

## report.json

```json
{
  "generated": "2026-10-24 21:46:28",
  "pipeline_version": "2026-10-25.11",
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
    "compile": 30173,
    "quarantined": 0,
    "fixed_by_model": 127,
    "rederived": 1,
    "rederived_by": {
      "faithful-pseudocode": 1
    }
  },
  "link": {
    "ok": true,
    "stubs": 19,
    "unresolved": 0
  },
  "improve": {},
  "organize": {
    "note": "final/program.c: 30173 functions",
    "written": true,
    "privacy_hits": 0
  },
  "stages": {
    "export": {
      "done": true,
      "started": "2026-10-24 21:32:31",
      "at": "2026-10-24 21:34:09",
      "seconds": 98,
      "note": "30489/30489 with pseudocode"
    },
    "rewrite": {
      "done": true,
      "started": "2026-10-24 21:34:11",
      "at": "2026-10-24 21:35:56",
      "seconds": 105,
      "model": "",
      "note": "30173/30489 rewritten",
      "model_busy": 12
    },
    "split": {
      "done": true,
      "started": "2026-10-24 21:35:56",
      "at": "2026-10-24 21:39:06",
      "seconds": 190,
      "note": "28984/30173 compile after the sweep"
    },
    "fix": {
      "done": true,
      "started": "2026-10-24 21:39:06",
      "at": "2026-10-24 21:44:05",
      "seconds": 299,
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "model_busy": 18
    },
    "recover": {
      "done": true,
      "started": "2026-10-24 21:44:05",
      "at": "2026-10-24 21:44:06",
      "seconds": 0,
      "model": "qwen2.5-coder-3b-instruct-mlx"
    },
    "privacy": {
      "done": true,
      "started": "2026-10-24 21:34:09",
      "at": "2026-10-24 21:34:11",
      "seconds": 2,
      "note": "1142 replacement(s)"
    },
    "link": {
      "done": true,
      "started": "2026-10-24 21:44:06",
      "at": "2026-10-24 21:46:09",
      "seconds": 123,
      "note": "linked"
    },
    "test": {
      "done": false,
      "started": "2026-10-24 21:46:09",
      "at": "2026-10-24 21:46:15",
      "note": "the rebuilt plugin didn't load: load executable"
    },
    "improve": {
      "done": false,
      "started": "2026-10-24 21:46:15",
      "at": "2026-10-24 21:46:15",
      "note": "off (--improve turns it on)"
    },
    "organize": {
      "done": true,
      "started": "2026-10-24 21:46:15",
      "at": "2026-10-24 21:46:28",
      "note": "final/program.c: 30173 functions",
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "seconds": 13
    }
  }
}
```

## build_state.json

```json
{
  "input_sha": "63b2ba1b109973f6",
  "split_done": true,
  "header_ok": true,
  "sweep_done": true,
  "version": "2026-10-18.1",
  "link_ok": true
}
```
