# Diagnostics — fastpass 3 — 2026-10-24 20:19:43


## Run

```
script: decomp_pipeline 2026-10-25.10 (build 2026-10-18.1)
command: /Users/admin/AIHarness/scripts/decomp_pipeline.py --workdir /Users/admin/glitchdecomp/fastpass 3 --from export --to organize --headless-export --ghidra-home /Users/admin/Downloads/ghidra_12.1.4_PUBLIC --project /Users/admin/glitchpt2.gpr --ctx 8192 --parallel 50 --workers 12 --lang c --no-pseudo --repair-minutes 1 --plugin /Users/admin/Downloads/Glitch_2_1_5_Mac_Free/Glitch2.component
python: 3.15.0 on darwin
compiler: /usr/bin/clang++ (clang)
compile flags: -Wno-c++11-narrowing -arch arm64
--ctx 8192, chars per token 2.06
model: qwen2.5-coder-3b-instruct-mlx
model requests turned down this run: 0, thinking-only answers: 0
fix stage model edits: {'calls': 11, 'no_answer': 3, 'rejected': 0}
```

## What the script struggled with

```

━━━━ what the script struggled with this run ━━━━
(errors it fixed on its own are left out; [also in the last N runs] marks the ones worth changing the script for)
rates (this run last; earlier runs above it):
  run                   compile %      quarantined %             to fix        fixer tried    fixer success %     fixer per hour  recover success %      learned fixes     learned kept %            rescued  ideas adopted/tested        test pass %
  10-24 18:26               100.0                0.0                  0                  -                  -                  -                  -                 96               98.1                  -                     -                0.0
  10-24 18:56               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
  10-24 19:28               100.0                0.0                  0                  1              100.0                 23                  -                 97               98.6                  -                     -                0.0
  10-24 19:54               100.0                0.0                  0                  2               50.0                 41                  -                 99               92.5                  -                     -                0.0
  10-24 20:19               100.0                0.0                  0                  3               33.3                 35                  -                104               98.6                  2                     -                0.0
couldn't handle:
  test          1 × the rebuilt plugin didn't load: load executable   [also in the last 4 run(s)]
                    → see build/test/test_report.txt
worked around (cost time, nothing lost):
  fix         119 × Ghidra globals / library functions nothing declared (declared once in shared.h)   e.g. LAB_001806a4   [also in the last 5 run(s)]
  fix           4 × fixes that undid each other (the cycle was stopped and the model got the function)   e.g. FUN_000cab20, insertText__16d864   [also in the last 2 run(s)]
  fix           3 × the model repeated an edit that had already failed (skipped)   e.g. insertText__16d864   [also in the last 1 run(s)]
  fix           2 × small edits the model couldn't give a usable answer for
  link         24 × functions replaced by placeholders to link   [also in the last 5 run(s)]
```

## Log of this run (pipeline.log)

```
[20:03:18] decomp_pipeline 2026-10-25.10: /Users/admin/glitchdecomp/fastpass 3 — stages export → organize
[20:03:18]   --ctx 8192: pieces up to 5303 characters, recover stage up to 11006
[20:03:18] ━━━━ Stage 1/10 · export ━━━━ getting every function's pseudocode from Ghidra (once — after that Ghidra can be closed)
[20:03:18]   using the existing ghidra_export.json (Ghidra not needed)
[20:03:26]   Ghidra lost the return value of 1507 function(s) (258 of them empty: they return what they're given), and 125 read an argument their signature doesn't have: fixing their signatures and decompiling them and their callers again (headless, read-only)
[20:04:18]   signature fix: 1507 function(s) given back their return value, 0 given the parameters they pass on (up the call chains), 4536 decompiled again with them
[20:04:25]   callgraph.json: 22076 functions with internal calls
[20:04:25]   export: 30489/30489 functions have pseudocode, 205 data types, 30489 signatures
[20:04:25] ━━━━ Stage 2/10 · privacy ━━━━ identifying information (names, web and email addresses, bundle IDs, paths, copyright lines) is replaced in Ghidra's export, before anything else sees it; what was replaced is kept in private/ on this Mac only
[20:04:27]   privacy: 1141 replacement(s) in Ghidra's export (6 names, 14 web addresses, 8 copyright lines, 1 email address, 3 user folders, 3 bundle IDs). What was replaced: private/privacy_report.txt (stays on this Mac)
[20:04:27]   privacy: 17 stand-in(s) are values the plugin uses while it runs (bundle ID, web addresses): the rebuilt plugin's Info.plist must use the same ones (listed in private/privacy_report.txt)
[20:04:27] ━━━━ Stage 3/10 · rewrite ━━━━ Ghidra's pseudocode is written out as one C file, with the program's data (no model: the code is what Ghidra decompiled)
[20:04:57]     functions with a system function's name (the system's is used): 3: sync, setbuf, objc_msgSend
[20:04:57]     Ghidra's copies of types the system headers define (the system's are used): 63, e.g. Byte, CGPoint, CGRect, CGSize, FILE, SEL
[20:04:57]     fields Ghidra named that the system's type calls something else (read at their offset): 14
[20:05:01]     pointers only the loader's fix-up list has (no reference in Ghidra): 583, fixed up too
[20:05:01]     static initializers the plugin runs when it loads (as the original does): 91
[20:05:01]     pointers in the data to addresses outside it (not fixed up): 7, listed in rewrite/data_unresolved_pointers.txt
[20:05:01]     data found by its address (not in Ghidra's label list): 496
[20:05:51]     addresses in the data written in the code as numbers ((long *)0x453400): 320, now the rebuilt data's
[20:06:05]     pieces of variables (v._0_8_): 6070
[20:06:05]     functions Ghidra said return nothing, whose callers use the result: 1929
[20:06:05]     16-byte register values (as gh16): 1791
[20:06:05]     C++/Objective-C names in definitions: 1285
[20:06:05]     C++ qualified names in code: 190
[20:06:05]     types C didn't know (declared opaque): 19
[20:06:05]     types that are also functions (as struct tags): 18
[20:06:05]     switches on a pointer (on its value): 11
[20:06:05]     NAN(x) tests (as isnan): 8
[20:06:05]     of those, returning a stand-in 0 (nothing to return in Ghidra's code): 537, listed in rewrite/lost_returns.txt
[20:06:10]     names that are a type and also a function (the type keeps its struct tag): 12
[20:06:10]   C source from Ghidra's pseudocode: 30173 function(s), 311 library stub(s) called directly, 29 data type(s) with Ghidra's layout, the program's data (35 block(s), 2997 labelled location(s) used, 33768 pointer fix-up(s), 1 placeholder(s) for data outside the export: rewrite/data_placeholders.txt) -> pseudocode.c
[20:06:10] ━━━━ Stage 4/10 · split ━━━━ libclang splits the rewrite into shared.h + one file per function, repairs the header, then compiles every function on its own
[20:10:42] ━━━━ Stage 5/10 · fix ━━━━ functions that don't compile are repaired, callees first: quick deterministic fixes, then the model; what can't be fixed is quarantined
[20:14:53]   fix: 23 model request(s); the model was busy 15% of the stage's 4m
[20:14:53] ━━━━ Stage 6/10 · recover ━━━━ quarantined functions are rebuilt from their Ghidra pseudocode
[20:14:53] ━━━━ Stage 7/10 · link ━━━━ the whole program is compiled and linked; anything still missing gets a placeholder and is listed in link_report.txt
[20:19:24] ━━━━ Stage 8/10 · test ━━━━ the rebuilt plugin and the original (--plugin) render the same test signals in a small test host; their outputs are compared sample by sample
[20:19:30]   test: the rebuilt plugin didn't load: crashed (SIGBUS) during: load executable
[20:19:30]   test: everything it saw is in /Users/admin/glitchdecomp/fastpass 3/build_c/test/test_report.txt
[20:19:30] ━━━━ Stage 9/10 · improve ━━━━ the code is made easier to read (names, Ghidra's helpers, casts, pointer arithmetic), worst functions first; a change is kept only if the function compiles to the same machine code, so the plugin does exactly what it did
[20:19:30]   improve: off (it's slow, and optional: the final code builds without it). Turn it on with --improve
[20:19:30] ━━━━ Stage 10/10 · organize ━━━━ the whole program is written out as one C source file, final/program.c, with its headers, its data and build.sh; final/ is only replaced once that builds
[20:19:43] ============================================================
[20:19:43] SUMMARY: 30173/30173 functions compile, 0 quarantined, 1 re-derived, link=OK
[20:19:43] Report: /Users/admin/glitchdecomp/fastpass 3/REPORT.md
[20:19:43] 
[20:19:43] ━━━━ what the script struggled with this run ━━━━
[20:19:43] (errors it fixed on its own are left out; [also in the last N runs] marks the ones worth changing the script for)
[20:19:43] rates (this run last; earlier runs above it):
[20:19:43]   run                   compile %      quarantined %             to fix        fixer tried    fixer success %     fixer per hour  recover success %      learned fixes     learned kept %            rescued  ideas adopted/tested        test pass %
[20:19:43]   10-24 18:26               100.0                0.0                  0                  -                  -                  -                  -                 96               98.1                  -                     -                0.0
[20:19:43]   10-24 18:56               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
[20:19:43]   10-24 19:28               100.0                0.0                  0                  1              100.0                 23                  -                 97               98.6                  -                     -                0.0
[20:19:43]   10-24 19:54               100.0                0.0                  0                  2               50.0                 41                  -                 99               92.5                  -                     -                0.0
[20:19:43]   10-24 20:19               100.0                0.0                  0                  3               33.3                 35                  -                104               98.6                  2                     -                0.0
[20:19:43] couldn't handle:
[20:19:43]   test          1 × the rebuilt plugin didn't load: load executable   [also in the last 4 run(s)]
[20:19:43]                     → see build/test/test_report.txt
[20:19:43] worked around (cost time, nothing lost):
[20:19:43]   fix         119 × Ghidra globals / library functions nothing declared (declared once in shared.h)   e.g. LAB_001806a4   [also in the last 5 run(s)]
[20:19:43]   fix           4 × fixes that undid each other (the cycle was stopped and the model got the function)   e.g. FUN_000cab20, insertText__16d864   [also in the last 2 run(s)]
[20:19:43]   fix           3 × the model repeated an edit that had already failed (skipped)   e.g. insertText__16d864   [also in the last 1 run(s)]
[20:19:43]   fix           2 × small edits the model couldn't give a usable answer for
[20:19:43]   link         24 × functions replaced by placeholders to link   [also in the last 5 run(s)]
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
why 2 function(s) are quarantined (first compile error, grouped):

     1  too few arguments to function call, expected N, have N
        e.g. insertText__16d864
     1  invalid operands to binary expression ('X' and 'X')
        e.g. FUN_000cab20
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

== proven: 104
[423 worked, 4 didn't] too few arguments to function call, expected N, have N (part of a line)
    @1();
  → @1(1);
[338 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(@4);
  → @1 = @3(@4);
[258 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1 = @2((@3)@4);
  → @1 = @2((@3)@4, 1);
[233 worked, 53 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
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
[104 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    (@1);
  → (@1, 1);
[89 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → *(unsigned char*)&@1 = @2(@3, @4);
[82 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16];
[73 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2.@3;
  → @1 = @2[8];
[73 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    )@1);
  → )@1, 1);
[70 worked, 12 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1*@2;
  → uint64_t @2;
[69 worked, 6 didn't] integer constant expression must have integer type, not 'X'
    case"" :
  → case 0 :
[64 worked, 2 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
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
[27 worked, 0 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1(@2
  → ((uint64_t(*)())@1)(@2
[25 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → unsigned char @1[16];@2(@3, @4);
[25 worked, 6 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2();
  → uint64_t @1 = @2();
[21 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5);
  → unsigned char @1[16] = {0};@2(@3, @4, @5);
[21 worked, 1 didn't] too few arguments to function call, expected at least N, have N (part of a line)
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
[13 worked, 0 didn't] too few arguments to function call, single argument 'X' was not specified (part of a line)
    @1()
  → ((uint64_t(*)())@1)()
[12 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned char @1[16] = {0};@2(@3, @4, @5, @6, @7, @8, @9);
[12 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(@2[0]);
  → @1(@2[0], 1);
[12 worked, 3 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = (*
  → unsigned char @1[16] = {0};(*
[11 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = 0;
  → @1[0] = 0;
[11 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\x01" :
  → case 1 :
[11 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = @2(@3());
  → @1 = @2(((uint64_t(*)())@3)());
[10 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    int @1 = (int)@2(
  → long @1 = @2(
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
[4 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(*(@2*)(@3+0x20));
  → ((uint64_t(*)())@1)(*(@2*)(@3+0x20));
[4 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    @1(@2()
  → @1(((uint64_t(*)())@2)()
[4 worked, 1 didn't] used type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (struct @2)@3(
  → @1 = @3(
[4 worked, 1 didn't] too few arguments to function call, expected N, have N (part of a line)
    (0x3ff0000000000000);
  → (0x3ff0000000000000, 0);
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
[3 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[1
  → ((uint64_t*)(uintptr_t)(@1))[1
[3 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1;
  → uint64_t @1 = 0;
[3 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1(@2, @3, @4, @5, @6, (long)@7[0], @8)
  → @1((unsigned char*)@2, @3, @4, @5, @6, (long)@7[0], @8);
[3 worked, 1 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = *(long*)((long)&@2.@3+@4);
  → @1 = *(long*)((long)@4[0x6a]+@4);
[3 worked, 1 didn't] used type 'X' (aka 'X') where arithmetic or pointer type is required
    (@1(@2, 3, @3), @3 = = (@4[4])@5(@6, 4, 4))){
  → (@1(@2, 3, @3), @5(@3, 0, 4) = = @5(@6, 4, 4))){
[3 worked, 1 didn't] used type 'X' (aka 'X') where arithmetic or pointer type is required (part of a line)
    ), @1 = = (@2[4])@3(
  → ), @3(@1, 0, 4) = = @3(
[3 worked, 1 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[2
  → ((uint64_t*)(uintptr_t)(@1))[2
[3 worked, 1 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    @1 = @2(@3
  → @1 = ((uint64_t(*)())@2)(@3

== candidate: 492
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
[2 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    *)@1(0x3ff0000000000000
  → *)((uint64_t(*)())@1)(0x3ff0000000000000
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
[2 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    if((@1)&& (@2 = @3(@4), @2 = = 0)){
  → if((@1)&& (@2 = ((uint64_t(*)())@3)(@4), @2 = = 0)){
[2 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1(@2, 0, 8, @3());
  → @1(@2, 0, 8, ((uint64_t(*)())@3)());
[2 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    8, @1()
  → 8, ((uint64_t(*)())@1)()
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
Run test: the rebuilt plugin against the original (2026-10-24 20:19:24)

original: Original.component
  architectures: x86_64, arm64; tested as arm64
rebuilt:  /Users/user?/name1decomp/fastpass 3/build_c/program.dylib (arm64)

packaged the rebuilt program as /Users/user?/name1decomp/fastpass 3/build_c/test/run-llblb0mp/Rebuilt.component (deleted after the test), with the original's Info.plist (35 privacy stand-in(s) applied) and its Resources folder linked in

== component Illformed: Name1 (aumf/igl2/DBlu)
factory: original AUPluginFactory; rebuilt AUPluginFactory (as in the original)
rebuilt plugin, loading: FAILED
crashed (SIGBUS) during: load executable
    CRASH signal=10 (SIGBUS: bad memory access) address=0x10abc9a34
    CRASH stack:
    0   aharness_host-arm64-325db53723      0x000000010486d2a4 on_crash + 196
    1   libsystem_platform.dylib            0x000000018d081744 _sigtramp + 56
    2   program                             0x000000010abc9a60 FUN_0020e3a0 + 16
    3   program                             0x000000010abc99ec FUN_0020e2fc + 12
    4   program                             0x000000010abc99b8 FUN_0020e27c + 28
    5   program                             0x000000010abc6714 FUN_0020bbe4 + 24
    6   program                             0x000000010ab9e8c0 FUN_001f04ac + 36
    7   program                             0x000000010ab9e9bc FUN_001f05ac + 12
    8   program                             0x000000010aedff30 gd_relocate + 4360
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
    25  aharness_host-arm64-325db53723      0x000000010486d628 open_unit + 204
    26  aharness_host-arm64-325db53723      0x000000010486c8c8 main + 248
    27  dyld                                0x000000018ccac4e4 start + 6992
    rebuilt functions in the stack (innermost first): FUN_0020e3a0 (funcs/_FUN_0020e3a0.cpp), FUN_0020e2fc (funcs/_FUN_0020e2fc.cpp), FUN_0020e27c (funcs/_FUN_0020e27c.cpp), FUN_0020bbe4 (funcs/_FUN_0020bbe4.cpp), FUN_001f04ac (funcs/_FUN_001f04ac.cpp), FUN_001f05ac (funcs/_FUN_001f05ac.cpp)
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
       x0 = 0x000000010abc9a2c  in the rebuilt program: FUN_0020e350 + 0xc
       x1 = 0x0000000000000000  (zero)
       x2 = 0x00000000000120a8
       x3 = 0x000000016b59100b
       x4 = 0x000000010aef6fec  in the rebuilt program: zoom_ + 0x145e0
       x5 = 0x000000016b591540
       x6 = 0x000000000000000a  (near zero)
       x7 = 0x0000000000000000  (zero)
       x8 = 0x000000010abc9a2c  in the rebuilt program: FUN_0020e350 + 0xc
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
      x19 = 0x000000016b591be8
      x20 = 0x000000010aedee28  in the rebuilt program: gd_relocate + 0x0
      x21 = 0x00000001f9801360
      x22 = 0x000000010aee38bc  in the rebuilt program: zoom_ + 0xeb0
      x23 = 0x000000010a8a4118
      x24 = 0x0000000000000006  (near zero)
      x25 = 0x00000000000000a0  (near zero)
      x26 = 0x000000010a8a4248
      x27 = 0x000000010a8a40c0
      x28 = 0x0000000000000010  (near zero)
       fp = 0x000000016b5914b0
       lr = 0x000000010abc9a60  in the rebuilt program: FUN_0020e3a0 + 0x10
       sp = 0x000000016b5914a0
       pc = 0x000000010abc9a68  in the rebuilt program: FUN_0020e3a0 + 0x18
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
         3 | uint64_t FUN_0020e24c(void)
         4 | {
         5 |   undefined8 in_x0;
         6 | 
         7 |   
         8 |   return (uint64_t)FUN_0020e26c(in_x0);
         9 | }
        10 | 
    Ghidra's pseudocode of FUN_0020e24c:
      void FUN_0020e24c(void)
      
      {
        undefined8 in_x0;
        
        FUN_0020e26c(in_x0);
        return;
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

the rebuilt plugin didn't load: crashed (SIGBUS) during: load executable
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

FUN_000037fc
FUN_00003e68
FUN_00005050
FUN_0000727c
FUN_000076a4
FUN_000087b8
FUN_0000973c
FUN_0000bb48
FUN_0000c1b8
FUN_0000f3c8
FUN_000116d0
FUN_00016dd0
FUN_00018e10
FUN_000195a4
FUN_0001bca4
FUN_00020be4
FUN_0002269c
FUN_000375f0
FUN_000532f4
FUN_00053364
FUN_00055104
FUN_00056e34
FUN_00059f20
FUN_000654e4
FUN_000678a4
FUN_00067a78
FUN_00067afc
FUN_00067e58
FUN_00067f34
FUN_0006806c
FUN_0006823c
FUN_00068308
FUN_00068f38
FUN_00069874
FUN_000698b8
FUN_00069a68
FUN_0006a514
FUN_0006ab90
FUN_0006ad64
FUN_0006ade8
FUN_0006b374
FUN_0006baf4
FUN_0006bd68
FUN_0006c300
FUN_0006c4d4
FUN_0006c558
FUN_0006cae4
FUN_0006d264
FUN_0006e058
FUN_00077000
FUN_00078900
FUN_00078954
FUN_00078a18
FUN_00078be8
FUN_00078cb4
FUN_0007971c
FUN_00079854
FUN_00079a48
FUN_0007ab28
FUN_0007b288
FUN_0007b3ec
FUN_0007c054
FUN_0007c098
FUN_0007cc4c
FUN_0007cdb4
FUN_0007e150
FUN_0007e1ac
FUN_0007ea74
FUN_0007ec40
FUN_0007ff4c
FUN_000800b0
FUN_000811d0
FUN_00081338
FUN_00084778
FUN_0008a134
FUN_0008a8b4
FUN_0008aa84
FUN_0008ab50
FUN_0008af74
FUN_0008b0dc
FUN_0008bacc
FUN_0008ce40
FUN_0008d2e0
FUN_00098a00
FUN_00098bd0
FUN_0009d504
FUN_0009e9ac
FUN_000a61d8
FUN_000a9888
FUN_000a9da4
FUN_000a9f90
FUN_000aa068
FUN_000aa870
FUN_000ab2ac
FUN_000ac208
FUN_000af700
FUN_000be348
FUN_000c5484
FUN_000c7a5c
FUN_000c8978
FUN_000c96a0
FUN_000cb488
FUN_000ce3e0
FUN_000d2d9c
FUN_000d4824
FUN_000d4b48
FUN_000d4c88
FUN_000d5310
FUN_000d5af0
FUN_000e7118
FUN_000e7bf4
FUN_000e7dec
FUN_000e7e64
FUN_000e8208
FUN_000e8308
FUN_000f695c
FUN_000ff0bc
FUN_00101b84
FUN_00101ccc
FUN_00101df8
FUN_00101ec8
FUN_00101f9c
FUN_00102098
FUN_00102184
FUN_0010a408
FUN_0010e070
FUN_00113bd0
FUN_00114b0c
FUN_0011a6d4
FUN_0011ad24
FUN_0011ba8c
FUN_0011c2e0
FUN_0011d550
FUN_0011e170
FUN_0011e1f8
FUN_001201fc
FUN_001264b4
FUN_00126508
FUN_00126844
FUN_00126898
FUN_00127d78
FUN_0012a6d8
FUN_0012b6fc
FUN_0012b764
FUN_0012c0c0
FUN_0012c0e0
FUN_0012c13c
FUN_0012c790
FUN_0012cc88
FUN_00138108
FUN_00138450
FUN_00138688
FUN_00138754
FUN_00139268
FUN_001393d0
FUN_00139754
FUN_001397b0
FUN_001397f4
FUN_00139b9c
FUN_0013b090
FUN_0013f30c
FUN_00141178
FUN_00141594
FUN_00144400
FUN_0014ed1c
FUN_0014edc4
FUN_0014f540
FUN_00150300
FUN_00150a94
FUN_001521bc
FUN_0015303c
FUN_00153598
FUN_00153640
FUN_00157c7c
FUN_0015a6d8
FUN_0016501c
FUN_00165250
FUN_0016543c
FUN_00165514
FUN_00165700
FUN_001657c4
FUN_00165e7c
FUN_0016644c
FUN_00166984
FUN_00166e98
FUN_00167138
FUN_001671a4
FUN_00167430
FUN_0016749c
FUN_0016e9d0
FUN_0016f134
FUN_0016f298
FUN_00171eb0
FUN_00173a94
FUN_00173ca4
FUN_00173dc8
FUN_001751cc
FUN_00175758
FUN_00175864
FUN_001a305c
FUN_001a30e4
FUN_001a314c
FUN_001a6724
FUN_001a6858
FUN_001a687c
FUN_001a68c8
FUN_001a68ec
FUN_001a7468
FUN_001a74bc
FUN_001a768c
FUN_001a8f80
FUN_001aaeb4
FUN_001ab088
FUN_001ab10c
FUN_001ab468
FUN_001abed8
FUN_001aea24
FUN_001aeb24
FUN_001af62c
FUN_001aff18
FUN_001b70d0
FUN_001b9628
FUN_001b9944
FUN_001b9b14
FUN_001b9be0
FUN_001b9ff8
FUN_001ba0f8
FUN_001ba1d8
FUN_001beb38
FUN_001beb8c
FUN_001bedb0
FUN_001bef84
FUN_001bf008
FUN_001bf35c
FUN_001bf3ec
FUN_001c0128
FUN_001c1d50
FUN_001c1e28
FUN_001c1e48
FUN_001c21e4
FUN_001c663c
FUN_001cd330
FUN_001cd55c
FUN_001cd62c
FUN_001cda50
FUN_001cdb50
FUN_001d4470
FUN_001d4b94
FUN_001d4d64
FUN_001d4e30
FUN_001d5290
FUN_001d53f8
FUN_001d5dd8
FUN_001d6f6c
FUN_001d71a8
FUN_001d72cc
FUN_001d7604
FUN_001d7704
FUN_001d97c4
FUN_001d9a00
FUN_001d9ab8
FUN_001d9df0
FUN_001da77c
FUN_001dfa88
FUN_001e1d90
FUN_001e1f90
FUN_001e21b0
FUN_001e2218
FUN_001e2298
FUN_001e256c
FUN_001e3b38
FUN_001e3d64
FUN_001e3e30
FUN_001e4248
FUN_001e4348
FUN_001e79ec
FUN_001e7aa4
FUN_001e7cb4
FUN_001e8240
FUN_001e8978
FUN_001ef378
FUN_001ef460
FUN_001efeac
FUN_001f1ab4
FUN_001f5464
FUN_001f54e4
FUN_001f896c
FUN_001f8fd0
FUN_001f9b30
FUN_001f9bc4
FUN_001f9ca8
FUN_001f9d50
FUN_001f9dec
FUN_001f9e9c
FUN_001fdadc
FUN_001fdcf0
FUN_001fde2c
FUN_001fe1a0
FUN_001fe1e4
FUN_001fed44
FUN_00202c84
FUN_00202cd8
FUN_00203100
FUN_00203154
FUN_00203430
FUN_00204254
FUN_0020530c
FUN_00205360
FUN_002054f4
FUN_002063b8
FUN_00206458
FUN_00206884
FUN_00208454
FUN_00208bd4
FUN_00208d74
FUN_00209648
FUN_00209754
FUN_0020a0e0
FUN_0020a1ec
FUN_0020d198
FUN_0020e23c
FUN_0020e350
FUN_0020e40c
FUN_0020e498
FUN_0020eb8c
FUN_0020eea8
FUN_0020ef28
FUN_0020f730
FUN_00211228
FUN_00212104
FUN_00213ec8
FUN_00215ca4
FUN_00216570
FUN_00218abc
FUN_00218b10
FUN_00218f58
FUN_0021996c
FUN_0021af00
FUN_00225e90
FUN_00225ef4
FUN_0022642c
FUN_00226490
FUN_002269b8
FUN_00226c24
FUN_00227700
FUN_00227974
FUN_0022bdd4
FUN_0022c018
FUN_0022c208
FUN_0022c2d4
FUN_0022c630
FUN_0022c674
FUN_0022ccd0
FUN_0022cd38
FUN_0022db14
FUN_0022e850
FUN_0022e930
FUN_00230f94
FUN_00231560
FUN_0023170c
FUN_00244830
FUN_002477c4
FUN_0024a2bc
FUN_0024f84c
FUN_002502f8
FUN_00250a70
FUN_0025275c
FUN_00253104
FUN_002541b8
FUN_0025519c
FUN_0025ae48
FUN_0025be8c
FUN_0025c000
FUN_0025c5ac
FUN_0025c698
FUN_0025ca14
FUN_0025cc8c
FUN_00266080
FUN_002675c4
FUN_00269f24
FUN_00269fcc
FUN_0026a0e0
FUN_0026a14c
FUN_0026a17c
FUN_0026a254
FUN_0026a2d4
FUN_0026a604
FUN_0026ae0c
FUN_0026ae3c
FUN_0026b4a0
FUN_0026b8c8
FUN_0026c260
FUN_0026c44c
FUN_0026c498
FUN_0026fc10
FUN_0026ff3c
FUN_00270228
FUN_00270e28
FUN_00270f38
FUN_002711d0
FUN_00271250
FUN_00271334
FUN_002713b8
FUN_0027167c
FUN_00271aa4
FUN_00272304
FUN_0027320c
FUN_002732a0
FUN_00273390
FUN_002739cc
FUN_0027cfa8
FUN_00280c9c
FUN_00280eac
FUN_00281018
FUN_0028116c
FUN_002812f8
FUN_002812fc
FUN_0028179c
FUN_002818dc
FUN_00281cf0
FUN_0028210c
FUN_0028269c
FUN_00282c5c
FUN_00284a84
FUN_00285ea8
FUN_00286298
FUN_002863d8
FUN_00286484
FUN_002867c0
FUN_00286b68
FUN_00286d94
FUN_0028d744
FUN_0028d7ec
FUN_0028d94c
FUN_0028dfa4
FUN_0028e060
FUN_0028e260
FUN_0028e748
FUN_0028e7e4
FUN_0028ec7c
FUN_00290b04
FUN_00290bb4
FUN_00290e08
FUN_00293328
FUN_002945bc
FUN_0029f9bc
FUN_0029fbec
FUN_002a0020
FUN_002a01e4
FUN_002a04a8
FUN_002a0ea4
FUN_002a1280
FUN_002a19d4
FUN_002a1aac
FUN_002a22a4
FUN_002b2c18
FUN_002c4bc4
FUN_002e9a6c
FUN_002eab84
FUN_002f0974
FUN_002f0af4
FUN_002f1024
FUN_002f19e4
FUN_002f1d78
FUN_002f1eb8
FUN_002f1fd0
FUN_002f4364
FUN_002f531c
FUN_002f712c
FUN_0030ab8c
FUN_0030f060
FUN_003149a4
FUN_00314bb4
FUN_00315318
FUN_0031eccc
FUN_0031ecfc
FUN_0031ef88
FUN_0031efb8
FUN_0031f244
FUN_0031f274
FUN_0031f3f0
FUN_0031f444
FUN_0031f4c8
FUN_0031f570
FUN_0031f7ac
FUN_0031f9bc
FUN_0031fda0
FUN_00320138
FUN_003213a0
FUN_00321770
FUN_00322700
FUN_00322a90
FUN_00323a20
FUN_00323db0
FUN_00325b30
FUN_00325c14
FUN_00325dbc
FUN_00325ec0
FUN_003261a0
FUN_00326cec
FUN_00326e2c
FUN_003271e4
FUN_0032758c
FUN_00327ad8
FUN_00327bc4
FUN_003280e4
FUN_003282b8
FUN_00330808
FUN_00330850
FUN_00334274
FUN_00335ea4
FUN_0033780c
FUN_0033b9a8
FUN_0033c9b4
FUN_0034894c
FUN_00348fa8
FUN_0034b684
FUN_0034c544
FUN_0034eb88
FUN_0035c508
FUN_0035f640
FUN_0035fc70
FUN_00366e0c
FUN_0036a158
FUN_0036a314
FUN_0036b730
FUN_003734c4
FUN_003774fc
FUN_00379c28
FUN_00381d64
FUN_00383b18
exception
iostream_385ed0
istream_385e94
operator__385ec4
runtime_error
streambuf_385ee8
```

## Build log of this run (build/worklist.log)

```
[20:06:10] build 2026-10-18.1 on /Users/admin/glitchdecomp/fastpass 3/rewrite/pseudocode.c
[20:06:10] Resume check (30173 functions in manifest):
[20:06:10]   the rewrite changed since the last build — updating the split (functions whose code changed get the new code; the others keep their fixes)
[20:06:10]   [redo] split + header: input changed — rebuilding shared.h/globals.cpp and merging with the work already done
[20:06:11]   libclang reported 2 error(s) in the declarations (saved to libclang_parse_errors.txt), e.g.:
[20:06:11]     _parse_monolith.cpp:220: static assertion failed due to requirement 'sizeof(struct section) == 80': Ghidra's size of section
[20:06:11]     _parse_monolith.cpp:236: static assertion failed due to requirement 'sizeof(struct segment_command) == 72': Ghidra's size of segment_command
[20:06:18]   split -> 30173 function TUs, 65 types (+37 forward decls), 30173 prototypes, 0 globals
[20:06:30]     functions: 3794 changed in the rewrite (new code taken), 207 already fixed by the model (kept), 26171 untouched (refreshed with the new split), 1 previously quarantined (restored for another try), 0 not in the old run
[20:06:30]     (the replaced versions are in /Users/admin/glitchdecomp/fastpass 3/snapshots/20261024-200619-build-update)
[20:06:30]   [redo] header check
[20:06:30]   » validate/repair shared headers
[20:06:31]   [redo] compile status
[20:06:31]   » preflight diagnose (surface any systemic cause before spending model time on 30173 functions)
[20:06:31]   preflight: sampled TUs compile — proceeding
[20:06:31]   » isolated compile sweep
[20:06:32]   compiling with 11 parallel worker(s)
[20:10:42]   isolated compile: 29748/30173 TUs pass, 425 need repair (251s)
[20:10:42]   status: 29748 compile, 425 still to fix, 0 quarantined
[20:14:01]   declared 119 name(s) the code uses that Ghidra's pseudocode has too (globals like DAT_..., library functions); compiling the 54 function(s) that use them again
[20:14:01]   compiling with 11 parallel worker(s)
[20:14:01]   isolated compile: 50/54 TUs pass, 4 need repair (1s)
[20:14:01]   LM Studio OK — using the loaded model qwen2.5-coder-3b-instruct-mlx
[20:14:01]   » dependency order + fixer loop
[20:14:01]   callgraph imported: 22076 callers, 64251 edges from callgraph.json
[20:14:02]   callgraph: 582 callee name(s) not in our TU set (external/library calls) — ignored for ordering
[20:14:02]   callgraph: exact deps for 21706/30173 functions
[20:14:02]     FUN_001f9ca8 -> fixed without the model
[20:14:02]     FUN_00208454 -> fixed without the model
[20:14:02]     FUN_00226bd0 -> fixed without the model
[20:14:02]     FUN_00227920 -> fixed without the model
[20:14:02]     FUN_001f9e9c -> fixed without the model
[20:14:02]     FUN_0012bfa8 -> fixed without the model
[20:14:02]     FUN_001e248c -> fixed without the model
[20:14:02]     FUN_001f9dec -> fixed without the model
[20:14:02]     FUN_0022c4e0 -> fixed without the model
[20:14:02]     FUN_0012bd48 -> fixed without the model
[20:14:02]     FUN_0011c380 -> fixed without the model
[20:14:02]     FUN_00212fd0 -> fixed without the model
[20:14:02]     FUN_0011d040 -> fixed without the model
[20:14:02]     FUN_00213f0c -> fixed without the model
[20:14:02]     FUN_0022c6ac -> fixed without the model
[20:14:02]     FUN_001c7904 -> fixed without the model
[20:14:02]     FUN_001cd8f4 -> fixed without the model
[20:14:02]     FUN_0023170c -> fixed without the model
[20:14:02]     FUN_001d74d8 -> fixed without the model
[20:14:02]     FUN_0011c800 -> fixed without the model
[20:14:02]     FUN_00018d88 -> fixed without the model
[20:14:02]     FUN_001e8194 -> fixed without the model
[20:14:02]     FUN_001d627c -> fixed without the model
[20:14:02]     FUN_0020eac8 -> fixed without the model
[20:14:03]     FUN_000c59b4 -> fixed without the model
[20:14:03]     FUN_0020f9f4 -> fixed without the model
[20:14:03]     FUN_001d5d98 -> fixed without the model
[20:14:03]     FUN_0020fa14 -> fixed without the model
[20:14:03]     FUN_001d0860 -> fixed without the model
[20:14:03]     FUN_001d072c -> fixed without the model
[20:14:03]     FUN_001d09c8 -> fixed without the model
[20:14:03]     FUN_001d0914 -> fixed without the model
[20:14:03]     FUN_001e40f8 -> fixed without the model
[20:14:03]     FUN_001e37c0 -> fixed without the model
[20:14:03]     FUN_00213b7c -> fixed without the model
[20:14:03]     FUN_001bf230 -> fixed without the model
[20:14:03]     FUN_001bef20 -> fixed without the model
[20:14:03]     FUN_001fe048 -> fixed without the model
[20:14:03]     FUN_00213964 -> fixed without the model
[20:14:03]     FUN_0013f530 -> fixed without the model
[20:14:03]     FUN_0013f62c -> fixed without the model
[20:14:03]     FUN_0013f8ec -> fixed without the model
[20:14:03]     FUN_002135c0 -> fixed without the model
[20:14:03]     FUN_0014193c -> fixed without the model
[20:14:03]     FUN_00223be4 -> fixed without the model
[20:14:03]     FUN_001edca0 -> fixed without the model
[20:14:03]     FUN_000eccc8 -> fixed without the model
[20:14:03]     FUN_00150980 -> fixed without the model
[20:14:03]     FUN_0014edf8 -> fixed without the model
[20:14:03]     FUN_0014f74c -> fixed without the model
[20:14:03]     FUN_001510f8 -> fixed without the model
[20:14:03]     FUN_00152200 -> fixed without the model
[20:14:03]     FUN_001515f0 -> fixed without the model
[20:14:03]     FUN_00223bc4 -> fixed without the model
[20:14:03]     FUN_00153468 -> fixed without the model
[20:14:03]     FUN_00153934 -> fixed without the model
[20:14:03]     FUN_00153660 -> fixed without the model
[20:14:03]     FUN_001537ac -> fixed without the model
[20:14:03]     FUN_001a7320 -> fixed without the model
[20:14:03]     FUN_001a80a4 -> fixed without the model
[20:14:03]     FUN_001be9f0 -> fixed without the model
[20:14:03]     FUN_001a1d80 -> fixed without the model
[20:14:03]     FUN_001bbebc -> fixed without the model
[20:14:03]     FUN_001c0b40 -> fixed without the model
[20:14:03]     FUN_000be83c -> fixed without the model
[20:14:03]     FUN_000be780 -> fixed without the model
[20:14:04]     FUN_001a353c -> fixed without the model
[20:14:04]     FUN_001e1e48 -> fixed without the model
[20:14:04]     FUN_000b19f8 -> fixed without the model
[20:14:04]     FUN_00003a04 -> fixed without the model
[20:14:04]     FUN_0004b344 -> fixed without the model
[20:14:04]     FUN_001a3394 -> fixed without the model
[20:14:04]     FUN_00202b58 -> fixed without the model
[20:14:04]     FUN_00203cd8 -> fixed without the model
[20:14:04]     FUN_001a41f8 -> fixed without the model
[20:14:04]     FUN_00202fd4 -> fixed without the model
[20:14:04]     FUN_00204afc -> fixed without the model
[20:14:04]     FUN_00067a14 -> fixed without the model
[20:14:04]     FUN_00067d08 -> fixed without the model
[20:14:04]     FUN_00069934 -> fixed without the model
[20:14:04]     FUN_00061330 -> fixed without the model
[20:14:04]     FUN_000649ac -> fixed without the model
[20:14:04]     FUN_0026ce1c -> fixed without the model
[20:14:04]     FUN_001a3a5c -> fixed without the model
[20:14:04]     FUN_00069748 -> fixed without the model
[20:14:04]     FUN_0008ae48 -> fixed without the model
[20:14:04]     FUN_0008afa8 -> fixed without the model
[20:14:04]     FUN_00086ed0 -> fixed without the model
[20:14:04]     FUN_0012636c -> fixed without the model
[20:14:04]     FUN_001266fc -> fixed without the model
[20:14:04]     FUN_00211c40 -> fixed without the model
[20:14:04]     FUN_00084778 -> fixed without the model
[20:14:04]     FUN_000b186c -> fixed without the model
[20:14:04]     FUN_002129e8 -> fixed without the model
[20:14:04]     FUN_00219784 -> fixed without the model
[20:14:04]     FUN_00219408 -> fixed without the model
[20:14:04]     FUN_00218990 -> fixed without the model
[20:14:05]     FUN_002051c8 -> fixed without the model
[20:14:05]     FUN_00205e80 -> fixed without the model
[20:14:05]     FUN_0021980c -> fixed without the model
[20:14:05]     FUN_001d9cc4 -> fixed without the model
[20:14:05]     FUN_00286c00 -> fixed without the model
[20:14:05]     FUN_00285690 -> fixed without the model
[20:14:05]     FUN_0012db5c -> fixed without the model
[20:14:05]     FUN_000a9f2c -> fixed without the model
[20:14:05]     FUN_0028674c -> fixed without the model
[20:14:05]     FUN_001f934c -> fixed without the model
[20:14:05]     FUN_00014e50 -> fixed without the model
[20:14:05]     FUN_0001b2dc -> fixed without the model
[20:14:05]     FUN_00023d48 -> fixed without the model
[20:14:05]     FUN_000171f8 -> fixed without the model
[20:14:05]     FUN_001a2588 -> fixed without the model
[20:14:05]     FUN_0002806c -> fixed without the model
[20:14:05]     FUN_001a3658 -> fixed without the model
[20:14:05]     FUN_00165dd0 -> fixed without the model
[20:14:05]     FUN_000315b0 -> fixed without the model
[20:14:05]     FUN_0016342c -> fixed without the model
[20:14:05]     FUN_001ab318 -> fixed without the model
[20:14:05]     FUN_000305a8 -> fixed without the model
[20:14:05]     FUN_001ab024 -> fixed without the model
[20:14:05]     FUN_001a374c -> fixed without the model
[20:14:05]     FUN_001a9e08 -> fixed without the model
[20:14:05]     FUN_000b8f30 -> fixed without the model
[20:14:05]     FUN_0003b010 -> fixed without the model
[20:14:05]     FUN_0003b7c0 -> fixed without the model
[20:14:05]     FUN_000471a8 -> fixed without the model
[20:14:06]     FUN_0004ab0c -> fixed without the model
[20:14:06]     FUN_00173144 -> fixed without the model
[20:14:06]     FUN_0004de00 -> fixed without the model
[20:14:06]     FUN_0004e5f8 -> fixed without the model
[20:14:06]     FUN_0002e28c -> fixed without the model
[20:14:06]     FUN_000b9730 -> fixed without the model
[20:14:06]     FUN_0004f15c -> fixed without the model
[20:14:06]     FUN_000532f4 -> fixed without the model
[20:14:06]     FUN_000ff0bc -> fixed without the model
[20:14:06]     FUN_00053364 -> fixed without the model
[20:14:06]     FUN_00053124 -> fixed without the model
[20:14:06]     FUN_00113540 -> fixed without the model
[20:14:06]     FUN_0005fcfc -> fixed without the model
[20:14:06]     FUN_000461e4 -> fixed without the model
[20:14:06]     FUN_000533dc -> fixed without the model
[20:14:06]     openShellWindow_60180 -> fixed without the model
[20:14:06]     FUN_0005c368 -> fixed without the model
[20:14:06]     FUN_0026909c -> fixed without the model
[20:14:06]     FUN_00225ea0 -> fixed without the model
[20:14:06]     FUN_0026b538 -> fixed without the model
[20:14:06]     FUN_0026ad3c -> fixed without the model
[20:14:06]     uiViewForAudioUnit_withSize_ -> fixed without the model
[20:14:06]     FUN_002721d4 -> fixed without the model
[20:14:06]     FUN_0011ff30 -> fixed without the model
[20:14:06]     FUN_0006b2c8 -> fixed without the model
[20:14:06]     FUN_0006ca38 -> fixed without the model
[20:14:06]     FUN_0006dbb8 -> fixed without the model
[20:14:06]     FUN_000787bc -> fixed without the model
[20:14:06]     FUN_001a9378 -> fixed without the model
[20:14:06]     FUN_00048c10 -> fixed without the model
[20:14:06]     FUN_000349a0 -> fixed without the model
[20:14:06]     FUN_0007bf04 -> fixed without the model
[20:14:07]     FUN_0007ea84 -> fixed without the model
[20:14:07]     FUN_00073024 -> fixed without the model
[20:14:07]     FUN_00079f84 -> fixed without the model
[20:14:07]     FUN_0007a1bc -> fixed without the model
[20:14:07]     FUN_00075344 -> fixed without the model
[20:14:07]     FUN_0008fe54 -> fixed without the model
[20:14:07]     FUN_000828e0 -> fixed without the model
[20:14:07]     FUN_000e80b8 -> fixed without the model
[20:14:07]     FUN_0007a408 -> fixed without the model
[20:14:07]     FUN_000e7784 -> fixed without the model
[20:14:07]     FUN_00088d48 -> fixed without the model
[20:14:07]     FUN_000cd0d8 -> fixed without the model
[20:14:07]     FUN_00227388 -> fixed without the model
[20:14:07]     FUN_0009d598 -> fixed without the model
[20:14:07]     FUN_0009f780 -> fixed without the model
[20:14:07]     FUN_000a352c -> fixed without the model
[20:14:07]     FUN_000cf2dc -> fixed without the model
[20:14:07]     FUN_000a1758 -> fixed without the model
[20:14:07]     FUN_000aa744 -> fixed without the model
[20:14:07]     FUN_000a7b50 -> fixed without the model
[20:14:07]     FUN_00270228 -> fixed without the model
[20:14:07]     FUN_00227144 -> fixed without the model
[20:14:07]     FUN_000b0234 -> fixed without the model
[20:14:07]     FUN_000a6694 -> fixed without the model
[20:14:07]     FUN_000b01d4 -> fixed without the model
[20:14:07]     FUN_000b091c -> fixed without the model
[20:14:07]     FUN_000b0638 -> fixed without the model
[20:14:07]     FUN_000b1034 -> fixed without the model
[20:14:07]     FUN_000b0698 -> fixed without the model
[20:14:07]     FUN_000b1cfc -> fixed without the model
[20:14:07]     FUN_000d0430 -> fixed without the model
[20:14:07]     FUN_000bc6c4 -> fixed without the model
[20:14:07]     FUN_000bd534 -> fixed without the model
[20:14:07]     FUN_000bdb6c -> fixed without the model
[20:14:07]     FUN_000bdae4 -> fixed without the model
[20:14:07]     FUN_000bf520 -> fixed without the model
[20:14:07]     FUN_0015933c -> fixed without the model
[20:14:07]     FUN_000d5230 -> fixed without the model
[20:14:08]     FUN_00099a34 -> fixed without the model
[20:14:08]     FUN_000cb488 -> fixed without the model
[20:14:08]     FUN_000c7158 -> fixed without the model
[20:14:08]     FUN_0011e170 -> fixed without the model
[20:14:08]     FUN_0011e1f8 -> fixed without the model
[20:14:08]     FUN_000d1a68 -> fixed without the model
[20:14:08]     FUN_000d4b48 -> fixed without the model
[20:14:08]     FUN_000d0c3c -> fixed without the model
[20:14:08]     FUN_000ca774 -> fixed without the model
[20:14:08]     FUN_000d5af0 -> fixed without the model
[20:14:08]     FUN_0011ab00 -> fixed without the model
[20:14:08]     FUN_0009a688 -> fixed without the model
[20:14:08]     FUN_000cbd04 -> fixed without the model
[20:14:08]     FUN_0011afa8 -> fixed without the model
[20:14:08]     FUN_000d61a8 -> fixed without the model
[20:14:08]     FUN_00023e68 -> fixed without the model
[20:14:08]     FUN_000d3d20 -> fixed without the model
[20:14:08]     FUN_000d6bec -> fixed without the model
[20:14:08]     FUN_000d7104 -> fixed without the model
[20:14:08]     FUN_001668d8 -> fixed without the model
[20:14:08]     FUN_0016374c -> fixed without the model
[20:14:09]     FUN_000f02dc -> fixed without the model
[20:14:09]     FUN_000ea3dc -> fixed without the model
[20:14:09]     FUN_000f5678 -> fixed without the model
[20:14:09]     FUN_000e6a1c -> fixed without the model
[20:14:09]     FUN_0011ad24 -> fixed without the model
[20:14:09]     FUN_000f660c -> fixed without the model
[20:14:09]     FUN_00112c78 -> fixed without the model
[20:14:09]     FUN_00101df8 -> fixed without the model
[20:14:09]     FUN_000eacc4 -> fixed without the model
[20:14:09]     FUN_00109dd8 -> fixed without the model
[20:14:09]     FUN_0010a09c -> fixed without the model
[20:14:09]     FUN_000fe7a0 -> fixed without the model
[20:14:09]     FUN_000fddd8 -> fixed without the model
[20:14:09]     FUN_000fe358 -> fixed without the model
[20:14:09]     FUN_000ff12c -> fixed without the model
[20:14:09]     FUN_000feb74 -> fixed without the model
[20:14:09]     FUN_00101b18 -> fixed without the model
[20:14:09]     FUN_00100548 -> fixed without the model
[20:14:09]     FUN_00101adc -> fixed without the model
[20:14:09]     FUN_00101c5c -> fixed without the model
[20:14:09]     FUN_00101d90 -> fixed without the model
[20:14:09]     FUN_00101ec8 -> fixed without the model
[20:14:09]     FUN_00101f38 -> fixed without the model
[20:14:09]     FUN_00101e60 -> fixed without the model
[20:14:09]     FUN_000b7074 -> fixed without the model
[20:14:09]     FUN_00102034 -> fixed without the model
[20:14:09]     FUN_00102120 -> fixed without the model
[20:14:10]     FUN_00101ccc -> fixed without the model
[20:14:10]     FUN_00105064 -> fixed without the model
[20:14:10]     FUN_000d4824 -> fixed without the model
[20:14:10]     FUN_001027bc -> fixed without the model
[20:14:10]     FUN_001084c4 -> fixed without the model
[20:14:10]     FUN_0010234c -> fixed without the model
[20:14:10]     FUN_00120648 -> fixed without the model
[20:14:10]     FUN_0010f698 -> fixed without the model
[20:14:10]     FUN_00109774 -> fixed without the model
[20:14:10]     FUN_000ac208 -> fixed without the model
[20:14:10]     FUN_0010fa24 -> fixed without the model
[20:14:10]     FUN_00106410 -> fixed without the model
[20:14:10]     FUN_00121510 -> fixed without the model
[20:14:10]     FUN_0010fdec -> fixed without the model
[20:14:10]     FUN_00121644 -> fixed without the model
[20:14:10]     FUN_00123694 -> fixed without the model
[20:14:10]     FUN_001a305c -> fixed without the model
[20:14:10]     FUN_00120960 -> fixed without the model
[20:14:10]     FUN_00132824 -> fixed without the model
[20:14:10]     FUN_0013913c -> fixed without the model
[20:14:10]     FUN_001aff18 -> fixed without the model
[20:14:10]     FUN_00139618 -> fixed without the model
[20:14:10]     FUN_00134180 -> fixed without the model
[20:14:10]     FUN_00135198 -> fixed without the model
[20:14:10]     FUN_00135ffc -> fixed without the model
[20:14:10]     FUN_0013fc48 -> fixed without the model
[20:14:10]     FUN_001653d8 -> fixed without the model
[20:14:10]     FUN_00124424 -> fixed without the model
[20:14:10]     FUN_00123e8c -> fixed without the model
[20:14:10]     FUN_001630a4 -> fixed without the model
[20:14:10]     FUN_0016569c -> fixed without the model
[20:14:11]     FUN_000eaad8 -> fixed without the model
[20:14:11]     FUN_00163110 -> fixed without the model
[20:14:11]     keyEquivalentFromMenuEntry__16b3b0 -> fixed without the model
[20:14:11]     FUN_0016f9a8 -> fixed without the model
[20:14:11]     FUN_001722dc -> fixed without the model
[20:14:11]     close_169730 -> fixed without the model
[20:14:11]     FUN_00176f44 -> fixed without the model
[20:14:11]     FUN_000eaec8 -> fixed without the model
[20:14:11]     FUN_001a3fa8 -> fixed without the model
[20:14:11]     FUN_00177824 -> fixed without the model
[20:14:11]     applicationDidBecomeActive_ -> fixed without the model
[20:14:11]     FUN_00123bf0 -> fixed without the model
[20:14:11]     FUN_00178094 -> fixed without the model
[20:14:11]     FUN_0018268c -> fixed without the model
[20:14:11]     FUN_0017929c -> fixed without the model
[20:14:11]     FUN_00182b5c -> fixed without the model
[20:14:11]     FUN_001807b4 -> fixed without the model
[20:14:11]     FUN_00189ea0 -> fixed without the model
[20:14:11]     FUN_0018b5cc -> fixed without the model
[20:14:11]     FUN_0018b914 -> fixed without the model
[20:14:11]     FUN_001926c4 -> fixed without the model
[20:14:11]     FUN_00188a38 -> fixed without the model
[20:14:11]     FUN_001723a0 -> fixed without the model
[20:14:11]     FUN_00194270 -> fixed without the model
[20:14:11]     FUN_00193f28 -> fixed without the model
[20:14:11]     FUN_001912c4 -> fixed without the model
[20:14:11]     updateLayerInRect__16ce54 -> fixed without the model
[20:14:12]     FUN_0019b0b0 -> fixed without the model
[20:14:12]     FUN_0019c938 -> fixed without the model
[20:14:12]     invalidate_1a8a74 -> fixed without the model
[20:14:12]     FUN_003836d4 -> fixed without the model
[20:14:12]     FUN_0019cc80 -> fixed without the model
[20:14:12]     FUN_001ae8f8 -> fixed without the model
[20:14:12]     FUN_00280ca4 -> fixed without the model
[20:14:12]     FUN_00199c00 -> fixed without the model
[20:14:12]     FUN_001ae170 -> fixed without the model
[20:14:12]     FUN_0027f4a0 -> fixed without the model
[20:14:12]     FUN_0028112c -> fixed without the model
[20:14:12]     FUN_00280ecc -> fixed without the model
[20:14:12]     FUN_0027f524 -> fixed without the model
[20:14:12]     FUN_00281728 -> fixed without the model
[20:14:12]     FUN_0028175c -> fixed without the model
[20:14:12]     FUN_0028209c -> fixed without the model
[20:14:12]     FUN_00327170 -> fixed without the model
[20:14:12]     FUN_002807ac -> fixed without the model
[20:14:12]     FUN_00327a38 -> fixed without the model
[20:14:12]     FUN_00326aec -> fixed without the model
[20:14:12]     FUN_003281a4 -> fixed without the model
[20:14:12]     FUN_001b432c -> fixed without the model
[20:14:12]     FUN_001b9e98 -> fixed without the model
[20:14:12]     FUN_001b8320 -> fixed without the model
[20:14:12]     FUN_001d5164 -> fixed without the model
[20:14:12]     FUN_001b7894 -> fixed without the model
[20:14:12]     FUN_001ba160 -> fixed without the model
[20:14:12]     FUN_001b8c8c -> fixed without the model
[20:14:12]     FUN_001d1544 -> fixed without the model
[20:14:12]     FUN_001a54e0 -> fixed without the model
[20:14:12]     FUN_00203e74 -> fixed without the model
[20:14:12]     FUN_00204c98 -> fixed without the model
[20:14:12]     FUN_00212b84 -> fixed without the model
[20:14:12]     FUN_0020601c -> fixed without the model
[20:14:12]     FUN_0022643c -> fixed without the model
[20:14:12]     FUN_002260dc -> fixed without the model
[20:14:12]     FUN_00228374 -> fixed without the model
[20:14:12]     FUN_001bce04 -> fixed without the model
[20:14:12]     FUN_002265a8 -> fixed without the model
[20:14:12]     FUN_00280990 -> fixed without the model
[20:14:13]     FUN_0031fcb0 -> fixed without the model
[20:14:13]     FUN_00320928 -> fixed without the model
[20:14:13]     FUN_00320b04 -> fixed without the model
[20:14:13]     FUN_0028fb48 -> fixed without the model
[20:14:13]     FUN_00320d00 -> fixed without the model
[20:14:13]     FUN_001725c4 -> fixed without the model
[20:14:13]     FUN_00321c9c -> fixed without the model
[20:14:13]     FUN_00320ed0 -> fixed without the model
[20:14:13]     FUN_00321e78 -> fixed without the model
[20:14:13]     FUN_002722a0 -> fixed without the model
[20:14:13]     FUN_00323198 -> fixed without the model
[20:14:13]     FUN_00322060 -> fixed without the model
[20:14:13]     FUN_00322230 -> fixed without the model
[20:14:13]     FUN_00322fbc -> fixed without the model
[20:14:13]     FUN_00323380 -> fixed without the model
[20:14:13]     FUN_002fb554 -> fixed without the model
[20:14:13]     FUN_00323550 -> fixed without the model
[20:14:13]     FUN_0032dc78 -> fixed without the model
[20:14:13]     FUN_0029ff78 -> fixed without the model
[20:14:13]     FUN_002a06ac -> fixed without the model
[20:14:13]     FUN_002a1934 -> fixed without the model
[20:14:13]     FUN_0029ffac -> fixed without the model
[20:14:13]     FUN_002a96d8 -> fixed without the model
[20:14:13]     FUN_002a0db8 -> fixed without the model
[20:14:13]     FUN_0030d24c -> fixed without the model
[20:14:13]     FUN_002a1ef0 -> fixed without the model
[20:14:13]     FUN_0030f060 -> fixed without the model
[20:14:13]     FUN_00327f3c -> fixed without the model
[20:14:13]     FUN_00326800 -> fixed without the model
[20:14:13]     FUN_001ad0a4 -> fixed without the model
[20:14:13]   quick fixes (no model): 372 of 375 function(s) compile now
[20:14:13]   fixer loop over 3 failing TU(s), dependency-ordered
[20:14:33]     [1/3] FUN_0013ec40 -> fixed (19s)
[20:14:34]   QUARANTINE FUN_000cab20: invalid operands to binary expression ('double' and 'unsigned int')
[20:14:34]     [2/3] FUN_000cab20 -> quarantined (20s)
[20:14:37]   QUARANTINE insertText__16d864: too few arguments to function call, expected 1, have 0
[20:14:37]     [3/3] insertText__16d864 -> quarantined (23s)
[20:14:37]   learned fixes on quarantined functions: 0 of 2 retried compile now
[20:14:37]   learned fixes: 104 proven, 492 being tried, 159 retired (8 new this run); used 480 of 487 time(s) tried, 99% kept; 0 quarantined function(s) rescued. All in build/learned_fixes.txt
[20:14:37]   model: 6 small edit(s) asked for, 2 without a usable edit
[20:14:37]   fixer loop done: 30171 compiling, 2 quarantined
[20:14:37]   why functions are quarantined (most common first; all in fix_report.txt):
[20:14:37]         1 × too few arguments to function call, expected N, have N  (e.g. insertText__16d864)
[20:14:37]         1 × invalid operands to binary expression ('X' and 'X')  (e.g. FUN_000cab20)
[20:14:37]   repair loop pass 1 (no model): 0 of 2 rescued
[20:14:46]     FUN_000cab20 -> fixed in the repair loop (model)
[20:14:48]   QUARANTINE insertText__16d864: assigning to 'gh16' from incompatible type 'undefined8' (aka 'unsigned long long')
[20:14:48]   repair loop pass 1 (model): 1 of 2 rescued
[20:14:48]   repair loop pass 2 (no model): 0 of 1 rescued
[20:14:52]     insertText__16d864 -> fixed in the repair loop (model)
[20:14:53]   repair loop pass 2 (model): 1 of 1 rescued
[20:14:53]   repair loop: 2 quarantined function(s) rescued
[20:19:19]   link round 1: linking 30176 objects ...
[20:19:21]   link round 1: 98 undefined, 0 duplicate symbol(s) — stubbed/quarantined, relinking
[20:19:22]   link round 2: linking 30177 objects ...
[20:19:23]   24 placeholder definition(s) in stubs.cpp (listed in link_report.txt)
[20:19:23]   LINK OK (round 2) -> /Users/admin/glitchdecomp/fastpass 3/build_c/program.dylib
[20:19:42]   previous final/ moved to /Users/admin/glitchdecomp/fastpass 3/snapshots/20261024-201942-final
[20:19:42]   final C source: /Users/admin/glitchdecomp/fastpass 3/final/program.c (30173 functions, 17.1 MB), built by final/build.sh into program.dylib
```

## pipeline_state.json

```json
{
  "stages": {
    "export": {
      "done": true,
      "started": "2026-10-24 20:03:18",
      "at": "2026-10-24 20:04:25",
      "seconds": 67,
      "note": "30489/30489 with pseudocode"
    },
    "rewrite": {
      "done": true,
      "started": "2026-10-24 20:04:27",
      "at": "2026-10-24 20:06:10",
      "seconds": 103,
      "model": "",
      "note": "30173/30489 rewritten",
      "model_busy": 12
    },
    "split": {
      "done": true,
      "started": "2026-10-24 20:06:10",
      "at": "2026-10-24 20:10:42",
      "seconds": 272,
      "note": "29748/30173 compile after the sweep"
    },
    "fix": {
      "done": true,
      "started": "2026-10-24 20:10:42",
      "at": "2026-10-24 20:14:53",
      "seconds": 250,
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "model_busy": 15
    },
    "recover": {
      "done": true,
      "started": "2026-10-24 20:14:53",
      "at": "2026-10-24 20:14:53",
      "seconds": 0,
      "model": "qwen2.5-coder-3b-instruct-mlx"
    },
    "privacy": {
      "done": true,
      "started": "2026-10-24 20:04:25",
      "at": "2026-10-24 20:04:27",
      "seconds": 2,
      "note": "1141 replacement(s)"
    },
    "link": {
      "done": true,
      "started": "2026-10-24 20:14:53",
      "at": "2026-10-24 20:19:24",
      "seconds": 271,
      "note": "linked"
    },
    "test": {
      "done": false,
      "started": "2026-10-24 20:19:24",
      "at": "2026-10-24 20:19:30",
      "note": "the rebuilt plugin didn't load: load executable"
    },
    "improve": {
      "done": false,
      "started": "2026-10-24 20:19:30",
      "at": "2026-10-24 20:19:30",
      "note": "off (--improve turns it on)"
    },
    "organize": {
      "done": true,
      "started": "2026-10-24 20:19:30",
      "at": "2026-10-24 20:19:42",
      "note": "final/program.c: 30173 functions",
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "seconds": 12
    }
  },
  "version": "2026-10-25.10",
  "chars_per_token": {
    "ctx": 8192,
    "value": 2.06
  },
  "struggles": [
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
    }
  ],
  "rates": [
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
    }
  ]
}
```

## report.json

```json
{
  "generated": "2026-10-24 20:19:42",
  "pipeline_version": "2026-10-25.10",
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
    "fixed_by_model": 119,
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
      "started": "2026-10-24 20:03:18",
      "at": "2026-10-24 20:04:25",
      "seconds": 67,
      "note": "30489/30489 with pseudocode"
    },
    "rewrite": {
      "done": true,
      "started": "2026-10-24 20:04:27",
      "at": "2026-10-24 20:06:10",
      "seconds": 103,
      "model": "",
      "note": "30173/30489 rewritten",
      "model_busy": 12
    },
    "split": {
      "done": true,
      "started": "2026-10-24 20:06:10",
      "at": "2026-10-24 20:10:42",
      "seconds": 272,
      "note": "29748/30173 compile after the sweep"
    },
    "fix": {
      "done": true,
      "started": "2026-10-24 20:10:42",
      "at": "2026-10-24 20:14:53",
      "seconds": 250,
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "model_busy": 15
    },
    "recover": {
      "done": true,
      "started": "2026-10-24 20:14:53",
      "at": "2026-10-24 20:14:53",
      "seconds": 0,
      "model": "qwen2.5-coder-3b-instruct-mlx"
    },
    "privacy": {
      "done": true,
      "started": "2026-10-24 20:04:25",
      "at": "2026-10-24 20:04:27",
      "seconds": 2,
      "note": "1141 replacement(s)"
    },
    "link": {
      "done": true,
      "started": "2026-10-24 20:14:53",
      "at": "2026-10-24 20:19:24",
      "seconds": 271,
      "note": "linked"
    },
    "test": {
      "done": false,
      "started": "2026-10-24 20:19:24",
      "at": "2026-10-24 20:19:30",
      "note": "the rebuilt plugin didn't load: load executable"
    },
    "improve": {
      "done": false,
      "started": "2026-10-24 20:19:30",
      "at": "2026-10-24 20:19:30",
      "note": "off (--improve turns it on)"
    },
    "organize": {
      "done": true,
      "started": "2026-10-24 20:19:30",
      "at": "2026-10-24 20:19:42",
      "note": "final/program.c: 30173 functions",
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "seconds": 12
    }
  }
}
```

## build_state.json

```json
{
  "input_sha": "192ea484b6d5351f",
  "split_done": true,
  "header_ok": true,
  "sweep_done": true,
  "version": "2026-10-18.1",
  "link_ok": true
}
```
