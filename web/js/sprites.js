/* The-Mailroom — hand-authored pixel sprites.
 *
 * Palette is derived from the AgentLaboratory artwork (warm paper/cream,
 * charcoal ink, logo-red accent, amber/gold highlights, dusty blue/teal/green
 * details). Every sprite is a matrix of palette keys; `.` is transparent.
 * All character sprites are 32 rows x 32 cols; props/small items vary.
 */

const PALETTE = {
  '.': null,          // transparent
  'k': '#202021',     // ink / outline
  'w': '#ffffff',     // white
  'p': '#faf3e6',     // paper cream
  'P': '#e8dcc3',     // paper shade
  'b': '#a48c6d',     // wood
  'B': '#684b32',     // wood dark
  'g': '#f7d156',     // gold
  'a': '#d9a866',     // amber
  'r': '#95272e',     // red (mailroom accent)
  'R': '#e26863',     // red light
  'u': '#577595',     // dusty blue
  'U': '#7d97b5',     // blue light
  't': '#659099',     // teal
  'T': '#9ec4c6',     // teal light
  'n': '#5f9e6e',     // green
  'N': '#8fd0a0',     // green light
  's': '#f2d4aa',     // skin
  'S': '#d3b391',     // skin shade
  'D': '#926a53',     // skin dark
  'H': '#50352c',     // hair brown
  'h': '#394951',     // hair black
  'L': '#b7c8cc',     // gray light
  'l': '#a09f9f',     // gray
  'd': '#5d5d5d',     // gray dark
  'm': '#7a4a3a',     // mouth
};
  '................................',
  '...........kkkkkk..............',
  '...........kHHHHHHk............',
  '...........kHHHHHHk............',
  '..........kHHHHHHHHk...........',
  '..........kssssssssk...........',
  '..........kssksskssk...........',
  '..........kssssssssk...........',
  '...........kssssssk............',
  '...........kkkkkkkk............',
  '..........kuuuuuuuuuuk.........',
  '..........kuuuuuuuuuuk.........',
  '..........kuuuuUUuuuuk.........',
  '..........kuuuuuuuuuuk.........',
  '.......sss.kkkkkkkk.sss........',
  '......kkkkkkkkkkkkkkkkkk.......',
  '......kbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk.......',
  '......kBBBBBBBBBBBBBBBBk.......',
  '......kBBBBBBBBBBBBBBBBk.......',
  '......kBBBBBBBBBBBBBBBBk.......',
  '......kBBBBBBBBBBBBBBBBk.......',
  '......kbbbbbbbbbbbbbbbbk.......',
  '......kkkkkkkkkkkkkkkkkk.......',
  '................................',
  '....kkkkk....kkkkk.............',
  '....kdddk....kdddk.............',
  '....kkkkk....kkkkk.............',
  '................................',
  '................................',
  '................................',
  '................................',
];

/* The mail-slot rack rises from the desk (drawn by floor as prop overlay). */
const SORTER_RACK = [
  '............................',
  '............................',
  '............................',
  '............................',
  '...................kkkkkkk..',
  '...................kpapapk..',
  '...................kpapapk..',
  '...................kpapapk..',
  '...................kpapapk..',
  '...................kkkkkkk..',
  '...................kpppppk..',
  '...................kpppppk..',
  '...................kkkkkkk..',
  '...................kpppppk..',
  '...................kpppppk..',
  '...................kkkkkkk..',
  '............................',
  '............................',
  '............................',];

/* CONTRACT specialist — tan coat, scroll + red seal prop. */
const SPECIALIST_CONTRACT = [
  '................................',
  '...........kkkkkk...............',
  '...........kHHHHHHk.............',
  '...........kHHHHHHk.............',
  '..........kHHHHHHHHk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........kpppppppppk...........',
  '..........kpppppppppk...........',
  '..........kppppUUppppk..........',
  '..........kpppppppppk...........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* CORPORATE specialist — dark blue coat, courthouse pediment prop. */
const SPECIALIST_CORPORATE = [
  '................................',
  '...........kkkkkk...............',
  '...........khhhhhhk.............',
  '...........khhhhhhk.............',
  '..........khhhhhhhhk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........kuuuuuuuuuuk..........',
  '..........kuuuuuuuuuuk..........',
  '..........kuuuuUUuuuuk..........',
  '..........kuuuuuuuuuuk..........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* DUE DILIGENCE — green coat, magnifying glass over papers prop. */
const SPECIALIST_DUE_DILIGENCE = [
  '................................',
  '...........kkkkkk...............',
  '...........kHHHHHHk.............',
  '...........kHHHHHHk.............',
  '..........kHHHHHHHHk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........knnnnnnnnnk...........',
  '..........knnnnnnnnnk...........',
  '..........knnnnUUnnnk...........',
  '..........knnnnnnnnnk...........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* CORRESPONDENCE — cream coat, quill + letter prop. */
const SPECIALIST_CORRESPONDENCE = [
  '................................',
  '...........kkkkkk...............',
  '...........kHHHHHHk.............',
  '...........kHHHHHHk.............',
  '..........kHHHHHHHHk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........kpppppppppk...........',
  '..........kpppppppppk...........',
  '..........kppppUUppppk..........',
  '..........kpppppppppk...........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* COMPLIANCE — teal coat, clipboard + checklist prop. */
const SPECIALIST_COMPLIANCE = [
  '................................',
  '...........kkkkkk...............',
  '...........kHHHHHHk.............',
  '...........kHHHHHHk.............',
  '..........kHHHHHHHHk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........ktttttttttk...........',
  '..........ktttttttttk...........',
  '..........kttttUUttttk..........',
  '..........ktttttttttk...........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* COURT OPINIONS — gray coat, gavel on book prop. */
const SPECIALIST_COURT = [
  '................................',
  '...........kkkkkk...............',
  '...........khhhhhhk.............',
  '...........khhhhhhk.............',
  '..........khhhhhhhhk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........klllllllllk...........',
  '..........klllllllllk...........',
  '..........kllllUUllllk..........',
  '..........klllllllllk...........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* BOSS — black hair, red tie, scales-of-justice prop above desk. */
const BOSS = [
  '................................',
  '...........kkkkkk...............',
  '...........khhhhhhk.............',
  '...........khhhhhhk.............',
  '..........khhhhhhhhk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........kuuuuuuuuuuk..........',
  '..........kuuuuuuuuuuk..........',
  '..........kuuuuuuuuuuk..........',
  '..........krrrrrrrrrrk..........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* REPORTER — gray hair, white shirt, typewriter prop with rising paper. */
const REPORTER = [
  '................................',
  '...........kkkkkk...............',
  '...........kLLllllk.............',
  '...........kLLllllk.............',
  '..........kLLllllllk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........kpppppppppk...........',
  '..........kpppppppppk...........',
  '..........kppppUUppppk..........',
  '..........kpppppppppk...........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* ARCHIVIST — brown hair, olive apron, filing cabinet drawn beside. */
const ARCHIVIST = [
  '................................',
  '...........kkkkkk...............',
  '...........kHHHHHHk.............',
  '...........kHHHHHHk.............',
  '..........kHHHHHHHHk............',
  '..........kssssssssk............',
  '..........kssksskssk............',
  '..........kssssssssk............',
  '...........kssssssk.............',
  '...........kkkkkkkk.............',
  '..........knnnnnnnnnk...........',
  '..........knnnnnnnnnk...........',
  '..........knnnnUUnnnk...........',
  '..........knnnnnnnnnk...........',
  '.......sss.kkkkkkkk.sss.........',
  '......kkkkkkkkkkkkkkkkkk........',
  '......kbbBBBBBBBBBBBBbbk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kBBBBBBBBBBBBBBBBk........',
  '......kbbbbbbbbbbbbbbbbk........',
  '......kkkkkkkkkkkkkkkkkk........',
  '................................',
  '....kkkkk....kkkkk..............',
  '....kdddk....kdddk..............',
  '....kkkkk....kkkkk..............',
  '................................',
  '................................',
  '................................',
  '................................',];

/* ---- station props (drawn on the desk top surface, row 15 area) ---- */
const PROP_SCROLL = [
  '..................kpppk',
  '.................kppppk',
  '................kpppppk',
  '...............kppppppk',
  '..............kpppppppk',
  '.............kppppppppk',
  '............kpppppppppk',
  '...........kppppppppppk',
  '............kppppppppk.',
  '.............kpppppppk.',
  '..............kppppppk.',
  '...............kpppppk.',
  '................kppppk.',
  '.................kpppk.',
  '..................krpk.',];
const PROP_SEAL = ['krk', 'kRk', 'kkk'];

const PROP_BUILDING = [
  '.......kkkkkkk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kkkkkkk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',
  '.......kpppppk.....',];

const PROP_MAGNIFIER = [
  '................kkkk..',
  '.............kkLLLLkk.',
  '...........kkLlllllLkk',
  '...........kLllllllLk.',
  '...........kLllTlllLk.',
  '...........kLllllllLk.',
  '............kLLLLLLk..',
  '.............kLLkkk...',
  '.............kLLk.....',
  '.............kLLk.....',
  '.............kLLk.....',
  '.............kkk......',];

const PROP_QUILL = [
  '..........kPPk',
  '.........kPppk',
  '........kPpppk',
  '.......kPppppk',
  '......kPpppppk',
  '.....kPppppppk',
  '......kppppppk',
  '.......kpppppk',
  '........kppppk',
  '.........kpppk',
  '..........kppk',
  '..........kpk.',
  '..........kRk.',
  '..........kkk.',];

const PROP_CLIPBOARD = [
  '........kkkkkkk',
  '........kpppppk',
  '........kpkpkpk',
  '........kpkpkpk',
  '........kpkpkpk',
  '........kpkpkpk',
  '........kpkpkpk',
  '........kpppppk',
  '........kkkkkkk',];

const PROP_GAVEL = [
  '..........kkkkk.',
  '..........kBBBBk',
  '..........kBBBBk',
  '..........kBBBBk',
  '..........kkkkk.',
  '..........kbbk..',
  '..........kbBk..',
  '..........kbBk..',
  '..........kbBk..',
  '..........kkk...',];

const PROP_SCALES = [
  '............kkkkkkkkkk',
  '...........kBgggggggBk',
  '..........kBBBgggBBBkk',
  '..........kbbBBBBBbbk.',
  '...........kkBbbbbBkk.',
  '............kBbbbbBk..',
  '............kBBBBBBk..',
  '.............kBbbBk...',
  '.............kBbbBk...',
  '.............kBbbBk...',
  '.............kBbbBk...',
  '.............kBbbBk...',
  '.............kBbbBk...',
  '.............kBbbBk...',
  '.............kkkkkk...',];

const PROP_TYPEWRITER = [
  '.................kkkkkkkk',
  '.................kppppppk',
  '.................kppppppk',
  '.................kppppppk',
  '.................kkkkkkkk',
  '.................kggggggk',
  '.................kggggggk',
  '.................kggggggk',
  '.................kkkkkkkk',
  '.................krrrrrrk',
  '.................krrrrrrk',
  '.................kkkkkkkk',];

const PROP_PAPER = [
  '.................kpppppppk',
  '.................kpppppppk',
  '.................kpppppppk',
  '.................kpppppppk',
  '.................kpppppppk',
  '.................kpppppppk',
  '.................kpppppppk',
  '.................kpppppppk',
  '.................kpppppppk',
  '.................kkkkkkkkk',];

const PROP_CABINET = [
  '..........kkkkkkkkkkk',
  '..........kBbbbbbbbBk',
  '..........kBppppppBk.',
  '..........kBpbbbbpBk.',
  '..........kBppppppBk.',
  '..........kBpbbbbpBk.',
  '..........kBppppppBk.',
  '..........kBpbbbbpBk.',
  '..........kBppppppBk.',
  '..........kBpbbbbpBk.',
  '..........kBppppppBk.',
  '..........kBbbbbbbBk.',
  '..........kkkkkkkkkkk',];

/* ---- envelope (20x14), tinted by doc-type via STAMP_COLORS ---- */
const ENVELOPE = [
  'kkkkkkkkkkkkkkkkkkkk',
  'kppppppppppppppppppk',
  'kpPppppppppppppppPpk',
  'kpPpRpppppppppppPppk',
  'kpPppppppppppppppPpk',
  'kpPppppppppppppppPpk',
  'kpPppppppppppppppPpk',
  'kpPppppppppppppppPpk',
  'kpPppppppppppppppPpk',
  'kpPppppppppppppppPpk',
  'kpPppppppppppppppPpk',
  'kpPppppppppppppppPpk',
  'kppppppppppppppppppk',
  'kkkkkkkkkkkkkkkkkkkk',];

/* ---- stamps (10x8) ---- */
const STAMP_APPROVED = [
  'kkkkkkkkkk',
  'knnnnnnnnk',
  'knNnnnnnnk',
  'knnNnnnnnk',
  'knnnnNnnnk',
  'knnnnnNnnk',
  'knnnnnnnnk',
  'kkkkkkkkkk',];

const STAMP_REVIEW = [
  'kkkkkkkkkk',
  'kggggggggk',
  'kggggggggk',
  'kgkgkgggk.',
  'kggggggggk',
  'kggkggkggk',
  'kggggggggk',
  'kkkkkkkkkk',];

const STAMP_FAILED = [
  'kkkkkkkkkk',
  'krrrrrrrrk',
  'krrrrrrrrk',
  'krrkrrkrrk',
  'krrrrrrrrk',
  'krrkrrkrrk',
  'krrrrrrrrk',
  'kkkkkkkkkk',];

/* ---- bins ---- */
const BIN_INBOX = [
  '......kkkkkkkkkkkkkk',
  '......kppppppppppppk',
  '......kpPppppppppPpk',
  '......kppppppppppppk',
  '......kppppppppppppk',
  '......kppppppppppppk',
  '......kppppppppppppk',
  '......kppppppppppppk',
  '......kbbbbbbbbbbbbk',
  '......kBBBBBBBBBBBBk',
  '......kkkkkkkkkkkkkk',];

const BIN_REVIEW = [
  '......kkkkkkkkkkkkkk',
  '......kppppppppppppk',
  '......kpgpgpgpgpgpgk',
  '......kppppppppppppk',
  '......kppppppppppppk',
  '......kbbbbbbbbbbbbk',
  '......kBBBBBBBBBBBBk',
  '......kkkkkkkkkkkkkk',];

const BIN_FAILED = [
  '......kkkkkkkkkkkkkk',
  '......krrrrrrrrrrrrk',
  '......krrrkkrrkkrrrk',
  '......krrrrrrrrrrrrk',
  '......krrrkkrrkkrrrk',
  '......krrrrrrrrrrrrk',
  '......kbbbbbbbbbbbbk',
  '......kBBBBBBBBBBBBk',
  '......kkkkkkkkkkkkkk',];

/* ---- conveyor roller tile (16x8) ---- */
const ROLLER = [
  'kkkkkkkkkkkkkkkk',
  'kbbbbbbbbbbbbbbk',
  'kbBBBBBBBBBBBBbk',
  'kBggggggggggggBk',
  'kBggggggggggggBk',
  'kbBBBBBBBBBBBBbk',
  'kbbbbbbbbbbbbbbk',
  'kkkkkkkkkkkkkkkk',];

/* ---- START / END terminals (18x12) ---- */
const NODE_START = [
  '....kkkkkkkkkkkkkk.',
  '..kknnnnnnnnnnnnkk.',
  '.knnNnnnnnnnnnnnnk.',
  '.knNnkkkkkkkkknNnk.',
  '.knNnknSSSSkknNnk..',
  '.knNnkSSSSSSknNnk..',
  '.knNnkSSSSSSknNnk..',
  '.knNnkkkkkkkkknNnk.',
  '.knNnnnnnnnnnnnnnk.',
  '.knnnnnnnnnnnnnnnk.',
  '..kkkkkkkkkkkkkkkk.',
  '...................',];

const NODE_END = [
  '....kkkkkkkkkkkkkk.',
  '..kkrrrrrrrrrrrrkk.',
  '.krrrrrrrrrrrrrrrk.',
  '.krrrkkkkkkkkrrrrk.',
  '.krrrkrRRRRkrrrrrk.',
  '.krrrkRRRRRRrrrrrk.',
  '.krrrkRRRRRRrrrrrk.',
  '.krrrkkkkkkkkrrrrk.',
  '.krrrrrrrrrrrrrrrk.',
  '.krrrrrrrrrrrrrrrk.',
  '..kkkkkkkkkkkkkkkk.',
  '...................',];

/* ---- lamp (6x8) ---- */
function lamp(color) {
  return [
    'kkkkkk',
    `k${color}${color}${color}${color}k`,
    `k${color}${color}${color}${color}k`,
    `k${color}${color}${color}${color}k`,
    'kkkkkk',
    '.kkkk.',
    '..kk..',
    '......',
  ];
}

const LAMP_GREEN = lamp('n');
const LAMP_RED = lamp('r');
const LAMP_GOLD = lamp('g');

/* Doc-type -> envelope stamp color + station accent. */
const DOC_TYPE_COLORS = {
  contract: '#7d97b5',
  corporate_record: '#659099',
  due_diligence: '#d9a866',
  correspondence: '#f2d4aa',
  compliance_filing: '#8fd0a0',
  court_opinion: '#e26863',
};
const DOC_TYPE_DEFAULT = '#a09f9f';

const SPRITES = {
  sorter: SORTER,
  specialist_contract: SPECIALIST_CONTRACT,
  specialist_corporate: SPECIALIST_CORPORATE,
  specialist_due_diligence: SPECIALIST_DUE_DILIGENCE,
  specialist_correspondence: SPECIALIST_CORRESPONDENCE,
  specialist_compliance: SPECIALIST_COMPLIANCE,
  specialist_court: SPECIALIST_COURT,
  boss: BOSS,
  reporter: REPORTER,
  archivist: ARCHIVIST,
  envelope: ENVELOPE,
  bin_inbox: BIN_INBOX,
  bin_review: BIN_REVIEW,
  bin_failed: BIN_FAILED,
  roller: ROLLER,
  node_start: NODE_START,
  node_end: NODE_END,
  lamp_green: LAMP_GREEN,
  lamp_red: LAMP_RED,
  lamp_gold: LAMP_GOLD,
};

/* Props keyed by station agent key. */
const PROPS = {
  sorter: { rows: SORTER_RACK, x: 21, y: 0 },
  specialist_contract: { rows: PROP_SCROLL, x: 11, y: 0 },
  specialist_corporate: { rows: PROP_BUILDING, x: 8, y: 0 },
  specialist_due_diligence: { rows: PROP_MAGNIFIER, x: 10, y: 0 },
  specialist_correspondence: { rows: PROP_QUILL, x: 11, y: 0 },
  specialist_compliance: { rows: PROP_CLIPBOARD, x: 12, y: 0 },
  specialist_court: { rows: PROP_GAVEL, x: 12, y: 0 },
  boss: { rows: PROP_SCALES, x: 9, y: 0 },
  reporter: { rows: PROP_PAPER, x: 10, y: 0 },
  archivist: { rows: PROP_CABINET, x: 12, y: 0 },
};

/* Draw a sprite onto a canvas context at integer pixel scale.
 * `tint` (optional) recolors the envelope stamp char 'R' -> a hex color. */
function drawSprite(ctx, rows, x, y, px, tint) {
  for (let r = 0; r < rows.length; r++) {
    const row = rows[r];
    for (let c = 0; c < row.length; c++) {
      const ch = row[c];
      if (ch === '.') continue;
      let color = PALETTE[ch];
      if (ch === 'R' && tint) color = tint;
      if (!color) continue;
      ctx.fillStyle = color;
      ctx.fillRect((x + c) * px, (y + r) * px, px, px);
    }
  }
}
