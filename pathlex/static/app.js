"use strict";

const I18N = {
  en: {
    skip: "Skip to main content",
    navLabel: "Primary navigation",
    languageLabel: "Interface language",
    brandHome: "PathLex home",
    roleChoiceLabel: "Choose a PathLex role",
    branchGraphLabel: "Finite branching story graph",
    heroMapLabel: "Illustration of vocabulary opportunities across story branches",
    targetNumber: "Target word {number}",
    navHome: "Home",
    navTeacher: "Teacher studio",
    navStudent: "Story library",
    footerScope: "Finite stories. Explicit constraints. No claim beyond the audited graph.",
    resetLanguage: "Reset language preference",
    serviceUp: "PathLex service is available.",
    serviceDown: "PathLex service is not reachable.",
    homeTitle: "Make every choice a learning path.",
    homeIntro:
      "PathLex plans a finite English story, checks vocabulary opportunities on every reachable branch, and shows exactly where a path still owes a word.",
    openStudio: "Design a story unit",
    browseStories: "Read a story",
    mapCaption: "A target counts only when its meaning, use, spacing, context, and practice mode fit the teacher’s specification.",
    mapStart: "start",
    mapExposure: "exposure",
    mapRetrieval: "retrieval",
    mapDebt: "debt",
    teacherRole: "For teachers",
    teacherRoleText: "Define what each target word must do, then inspect the complete branch map before publishing.",
    teacherRoleAction: "Open teacher studio",
    studentRole: "For learners",
    studentRoleText: "Read an English story, make consequential choices, and answer before feedback reveals the target word.",
    studentRoleAction: "Open story library",
    teacherTitle: "Plan the learning opportunities first.",
    teacherIntro:
      "Describe the learners, the target uses, and the finite branch shape. PathLex will allocate opportunities before it asks the language model to write.",
    storyBrief: "Story brief",
    storyBriefHelp: "Give the generator the language boundary and a clear narrative direction.",
    titleLabel: "Unit title",
    titlePlaceholder: "The lighthouse after midnight",
    themeLabel: "Story theme",
    themePlaceholder: "A coastal mystery with a hopeful ending",
    cefrLabel: "English level",
    knownLabel: "Learners’ known vocabulary",
    knownPlaceholder: "arrive, boat, bright, carry, decide",
    knownHint: "Comma or line separated. These words may be used freely.",
    baseLabel: "Allowed foundation vocabulary",
    basePlaceholder: "a, the, be, have, go, look",
    baseHint: "Keep this list explicit for tighter language control.",
    safetyLabel: "Content and culture boundaries",
    safetyPlaceholder: "No violence; suitable for university learners; avoid stereotypes.",
    topology: "Branch shape",
    topologyHelp: "A finite graph can be fully enumerated. Larger graphs may exceed the configured path budget.",
    depthLabel: "Story depth",
    branchLabel: "Choices per branch",
    maxPathsLabel: "Maximum paths",
    commonPrefixLabel: "Common-prefix opportunity limit",
    commonPrefixHint: "Maximum share of target opportunities allowed before the first choice.",
    targets: "Target lexical units",
    targetsHelp: "A word form alone is not enough. Specify the intended meaning and use.",
    addTarget: "Add target word",
    removeTarget: "Remove",
    targetWord: "Target word",
    targetWordPlaceholder: "navigate",
    sense: "Target meaning or gloss",
    sensePlaceholder: "to find or plan a route",
    partOfSpeech: "Part of speech",
    posVerb: "verb",
    posNoun: "noun",
    posAdjective: "adjective",
    posAdverb: "adverb",
    posOther: "other",
    allowedCollocations: "Required or allowed uses",
    allowedPlaceholder: "navigate a route, navigate through",
    forbiddenCollocations: "Uses to avoid",
    forbiddenPlaceholder: "navigate a person",
    contexts: "Context categories",
    contextsPlaceholder: "travel, problem solving, directions",
    phases: "Required story phases",
    phasesPlaceholder: "opening, middle, ending",
    positiveExamples: "Positive examples",
    positivePlaceholder: "We used the stars to navigate through the fog.",
    negativeExamples: "Counterexamples",
    negativePlaceholder: "The captain navigated me the map.",
    occurrenceCount: "Minimum opportunities",
    minGap: "Minimum node gap",
    maxGap: "Maximum node gap",
    minContexts: "Minimum contexts",
    modeExposure: "Reading",
    modeJudgment: "Choice judgment",
    modeRetrieval: "Active retrieval",
    modesHint: "Required counts by practice mode. Remaining opportunities become reading exposures.",
    compileStory: "Plan and generate story",
    compileNote: "Generation requires a configured LLM key. Structural infeasibility is reported separately from model failure.",
    compiling: "Planning every reachable path…",
    existingUnits: "Saved story units",
    noSavedUnits: "No story units have been saved yet.",
    loadUnit: "Inspect unit",
    auditEmptyTitle: "The branch map will appear here.",
    auditEmptyText: "Complete the brief and add at least one target word. PathLex will first prove whether the requested slots fit the finite graph.",
    auditStatus: "Operational status",
    auditWorstCoverage: "Worst-path coverage",
    auditPathPass: "Paths satisfying all constraints",
    auditPaths: "Reachable terminal paths",
    auditCalls: "Model calls",
    auditDebts: "Unpaid vocabulary opportunities",
    auditReasonCodes: "Planner reason codes",
    noDebts: "No path-level debt is currently reported.",
    pathLabel: "Path",
    refresh: "Refresh status",
    repair: "Repair the worst path",
    repairing: "Rechecking affected branches…",
    publish: "Publish for learners",
    published: "Published",
    exportJson: "Export unit JSON",
    publishGate: "Only a VERIFIED finite graph can be published.",
    status_PLAN_FEASIBLE: "Slot plan is feasible",
    status_PLAN_INFEASIBLE: "Requested constraints are structurally infeasible",
    status_UNSAT: "Requested constraints are structurally infeasible",
    status_GENERATING: "Story text is being generated",
    status_VERIFYING: "Generated text is being checked",
    status_VERIFIED: "Every reachable path passed the configured checks",
    status_COUNTEREXAMPLE: "At least one reachable path has a constraint debt",
    status_UNKNOWN: "The complete graph could not be verified",
    status_GENERATION_FAILURE: "The language model did not produce a usable graph",
    status_DRAFT: "Draft",
    status_QUEUED: "Waiting to compile",
    status_PLANNING: "Checking finite slot feasibility",
    libraryTitle: "Choose where the story turns.",
    libraryIntro: "Every published unit is finite and has passed its configured path audit. Story prose remains in English; instructions and feedback follow your interface language.",
    libraryLoading: "Loading the story library…",
    libraryEmptyTitle: "No verified stories are published.",
    libraryEmptyText: "Ask a teacher to publish a verified unit, or create one in the teacher studio.",
    goTeacher: "Create a story unit",
    cefrMeta: "Level {level}",
    targetMeta: "{count} target words",
    pathMeta: "{count} paths",
    playStory: "Start this story",
    startingStory: "Opening the first branch…",
    backLibrary: "Back to library",
    storyProgress: "Story progress: {current} of {total}",
    retrievalTitle: "Answer before the story reveals the word",
    retrievalPlaceholder: "Type your answer",
    checkAnswer: "Check answer",
    checkingAnswer: "Checking…",
    chooseNext: "What happens next?",
    choiceLocked: "Answer the vocabulary prompt before choosing a branch.",
    journeyComplete: "This path is complete.",
    completeText: "You reached one ending. The path record is saved for this session; it is not a test score.",
    readAnother: "Choose another story",
    replay: "Start this story again",
    loading: "Loading…",
    requiredError: "Complete the required fields before continuing.",
    targetError: "Each target needs a word, a target meaning, and at least one opportunity.",
    gapError: "A maximum gap cannot be smaller than the minimum gap.",
    modeError: "Required practice-mode counts cannot exceed the minimum opportunity count.",
    contextCountError: "Minimum contexts cannot exceed the number of explicit context categories.",
    phaseError: "Story phases must be opening, middle, or ending.",
    topologyError: "This branch shape exceeds the maximum path count. Reduce depth or branching.",
    answerRequired: "Enter an answer before checking it.",
    apiError: "The service could not complete this request. Check the configuration and try again.",
    networkError: "The PathLex service is not reachable. Start the server and retry.",
    publishedToast: "Published for learners.",
    repairedToast: "Repair finished. Review the new audit status.",
    exportedToast: "Unit JSON exported.",
    languageResetToast: "Language preference cleared. English is now the default.",
    unitNotFound: "This story unit could not be found.",
    sessionNotFound: "This reading session could not be found.",
    feedbackLabel: "Feedback",
    answerRecorded: "Your answer was recorded before feedback was shown.",
    supportTitle: "Story support",
    finishEnding: "Finish this path",
    finishingEnding: "Saving this ending…",
    error_INVALID_INPUT: "Some input is invalid. Review the requirements and try again.",
    error_PLAYER_ERROR: "This story action is not available in the current state.",
    error_NOT_FOUND: "The requested PathLex record could not be found.",
    error_CONFLICT: "This action conflicts with the unit’s current state. Refresh and try again.",
    error_INTERNAL_ERROR: "The service could not complete this request. Check the server log and retry.",
    unitError_LLM_NOT_CONFIGURED: "Configure the LLM API key, then create a new unit.",
    unitError_PLAN_INFEASIBLE: "The requested slots do not fit this finite graph. Adjust depth, spacing, or opportunity counts.",
    unitError_GENERATION_FAILURE: "The model did not return a complete structurally usable graph.",
    unitError_VERIFICATION_UNKNOWN: "At least one opportunity lacks a sufficiently certain verification decision.",
    unitError_COUNTEREXAMPLE: "A reachable path still has an explicit vocabulary opportunity debt.",
    unitError_COMPILATION_FAILED: "Compilation stopped unexpectedly. Review the server log and retry with a new unit.",
    unitError_REPAIR_FAILED: "The repair operation stopped unexpectedly; the unit was closed as UNKNOWN.",
    operationalNotice: "This audit is an operational check of one generated unit, not evidence that the method improves learning.",
  },
  zh: {
    skip: "跳到主要内容",
    navLabel: "主导航",
    languageLabel: "界面语言",
    brandHome: "PathLex 首页",
    roleChoiceLabel: "选择 PathLex 使用入口",
    branchGraphLabel: "有限分支故事图",
    heroMapLabel: "词汇教学机会在故事分支中分布的示意图",
    targetNumber: "目标词 {number}",
    navHome: "首页",
    navTeacher: "教师工作台",
    navStudent: "故事库",
    footerScope: "有限故事，明确约束；不对已审计图以外作保证。",
    resetLanguage: "重置语言偏好",
    serviceUp: "PathLex 服务可用。",
    serviceDown: "无法连接 PathLex 服务。",
    homeTitle: "让每个选择都成为学习路径。",
    homeIntro: "PathLex 先规划有限英语故事，再检查每条可达分支上的词汇教学机会，并明确指出哪条路径仍欠缺哪个词。",
    openStudio: "设计故事单元",
    browseStories: "阅读故事",
    mapCaption: "只有词义、用法、间隔、语境和练习方式都符合教师规范时，目标词才计为一次合格机会。",
    mapStart: "开始",
    mapExposure: "阅读接触",
    mapRetrieval: "主动提取",
    mapDebt: "机会欠缺",
    teacherRole: "教师入口",
    teacherRoleText: "定义每个目标词需要完成的教学任务，发布前检查完整分支图。",
    teacherRoleAction: "打开教师工作台",
    studentRole: "学习者入口",
    studentRoleText: "阅读英语故事，作出会改变情节的选择，并在反馈显示目标词前先作答。",
    studentRoleAction: "打开故事库",
    teacherTitle: "先规划教学机会，再生成故事。",
    teacherIntro: "说明学习者水平、目标用法和有限分支形状。PathLex 会先分配机会槽位，再请求语言模型写作。",
    storyBrief: "故事要求",
    storyBriefHelp: "为生成器划定语言边界，并给出清楚的叙事方向。",
    titleLabel: "单元标题",
    titlePlaceholder: "午夜后的灯塔",
    themeLabel: "故事主题",
    themePlaceholder: "发生在海岸、以希望收尾的谜案",
    cefrLabel: "英语水平",
    knownLabel: "学生已掌握词汇",
    knownPlaceholder: "arrive, boat, bright, carry, decide",
    knownHint: "用逗号或换行分隔；系统可以自由使用这些词。",
    baseLabel: "允许使用的基础词汇",
    basePlaceholder: "a, the, be, have, go, look",
    baseHint: "明确列出基础词可以提高语言难度控制。",
    safetyLabel: "内容与文化边界",
    safetyPlaceholder: "不出现暴力；适合大学学习者；避免刻板印象。",
    topology: "分支形状",
    topologyHelp: "有限图才能被完整枚举；图过大时可能超过路径预算。",
    depthLabel: "故事深度",
    branchLabel: "每个分支的选项数",
    maxPathsLabel: "最大路径数",
    commonPrefixLabel: "共同前缀机会比例上限",
    commonPrefixHint: "首次选择之前允许承载的目标机会最大比例。",
    targets: "目标词汇单元",
    targetsHelp: "只有词形不够，还需要说明目标词义和具体用法。",
    addTarget: "添加目标词",
    removeTarget: "移除",
    targetWord: "目标词",
    targetWordPlaceholder: "navigate",
    sense: "目标词义或释义",
    sensePlaceholder: "寻找或规划路线",
    partOfSpeech: "词性",
    posVerb: "动词",
    posNoun: "名词",
    posAdjective: "形容词",
    posAdverb: "副词",
    posOther: "其他",
    allowedCollocations: "要求或允许的用法",
    allowedPlaceholder: "navigate a route, navigate through",
    forbiddenCollocations: "禁止的用法",
    forbiddenPlaceholder: "navigate a person",
    contexts: "语境类别",
    contextsPlaceholder: "旅行、解决问题、方向",
    phases: "要求出现的故事阶段",
    phasesPlaceholder: "opening, middle, ending",
    positiveExamples: "正例",
    positivePlaceholder: "We used the stars to navigate through the fog.",
    negativeExamples: "反例",
    negativePlaceholder: "The captain navigated me the map.",
    occurrenceCount: "最低合格机会数",
    minGap: "最小节点间隔",
    maxGap: "最大节点间隔",
    minContexts: "最少语境数",
    modeExposure: "阅读接触",
    modeJudgment: "选择判断",
    modeRetrieval: "主动提取",
    modesHint: "按练习方式规定最低次数，其余机会默认作为阅读接触。",
    compileStory: "规划并生成故事",
    compileNote: "生成需要配置 LLM 密钥。结构不可满足与模型生成失败会被分别报告。",
    compiling: "正在规划每条可达路径……",
    existingUnits: "已保存的故事单元",
    noSavedUnits: "尚未保存故事单元。",
    loadUnit: "查看单元",
    auditEmptyTitle: "分支图将在这里显示。",
    auditEmptyText: "填写故事要求并添加至少一个目标词。PathLex 会先判断有限图能否容纳所需机会槽位。",
    auditStatus: "运行状态",
    auditWorstCoverage: "最差路径覆盖率",
    auditPathPass: "满足全部约束的路径",
    auditPaths: "可达终止路径",
    auditCalls: "模型调用次数",
    auditDebts: "尚未满足的词汇机会",
    auditReasonCodes: "规划器原因代码",
    noDebts: "当前未报告路径级机会欠缺。",
    pathLabel: "路径",
    refresh: "刷新状态",
    repair: "修复最差路径",
    repairing: "正在重新检查受影响的分支……",
    publish: "发布给学习者",
    published: "已发布",
    exportJson: "导出单元 JSON",
    publishGate: "只有状态为 VERIFIED 的有限图才能发布。",
    status_PLAN_FEASIBLE: "机会槽位规划可行",
    status_PLAN_INFEASIBLE: "请求的约束在结构上不可满足",
    status_UNSAT: "请求的约束在结构上不可满足",
    status_GENERATING: "正在生成故事文本",
    status_VERIFYING: "正在检查生成文本",
    status_VERIFIED: "每条可达路径均通过已配置检查",
    status_COUNTEREXAMPLE: "至少一条可达路径仍有约束欠缺",
    status_UNKNOWN: "无法验证完整故事图",
    status_GENERATION_FAILURE: "语言模型未生成可用故事图",
    status_DRAFT: "草稿",
    status_QUEUED: "等待编译",
    status_PLANNING: "正在检查有限槽位可行性",
    libraryTitle: "选择故事转向何处。",
    libraryIntro: "每个已发布单元都是有限故事，并已通过所配置的路径审计。故事正文保持英语，说明和反馈使用当前界面语言。",
    libraryLoading: "正在加载故事库……",
    libraryEmptyTitle: "尚无已发布的验证故事。",
    libraryEmptyText: "请教师发布一个已验证单元，或前往教师工作台创建。",
    goTeacher: "创建故事单元",
    cefrMeta: "{level} 级",
    targetMeta: "{count} 个目标词",
    pathMeta: "{count} 条路径",
    playStory: "开始故事",
    startingStory: "正在打开第一个分支……",
    backLibrary: "返回故事库",
    storyProgress: "故事进度：{current}/{total}",
    retrievalTitle: "先回答，再让故事显示目标词",
    retrievalPlaceholder: "输入答案",
    checkAnswer: "检查答案",
    checkingAnswer: "正在检查……",
    chooseNext: "接下来会发生什么？",
    choiceLocked: "完成词汇作答后才能选择分支。",
    journeyComplete: "这条路径已经结束。",
    completeText: "你已到达一个结局。本次路径记录已保存，但它不是测验分数。",
    readAnother: "选择另一个故事",
    replay: "重新开始这个故事",
    loading: "正在加载……",
    requiredError: "请先填写必填项。",
    targetError: "每个目标词都需要词形、目标词义和至少一次教学机会。",
    gapError: "最大间隔不能小于最小间隔。",
    modeError: "各练习方式的最低次数总和不能超过最低合格机会数。",
    contextCountError: "最少语境数不能超过已填写的语境类别数。",
    phaseError: "故事阶段只能填写 opening、middle 或 ending。",
    topologyError: "该分支形状超过最大路径数，请减少深度或分支数。",
    answerRequired: "输入答案后再检查。",
    apiError: "服务无法完成请求，请检查配置后重试。",
    networkError: "无法连接 PathLex 服务，请启动服务后重试。",
    publishedToast: "已发布给学习者。",
    repairedToast: "修复已完成，请检查新的审计状态。",
    exportedToast: "单元 JSON 已导出。",
    languageResetToast: "语言偏好已清除，界面恢复默认英文。",
    unitNotFound: "找不到这个故事单元。",
    sessionNotFound: "找不到这次阅读会话。",
    feedbackLabel: "反馈",
    answerRecorded: "系统已在显示反馈前记录你的答案。",
    supportTitle: "故事提示",
    finishEnding: "结束这条路径",
    finishingEnding: "正在保存这个结局……",
    error_INVALID_INPUT: "部分输入不符合要求，请检查约束后重试。",
    error_PLAYER_ERROR: "当前故事状态不允许此操作。",
    error_NOT_FOUND: "找不到请求的 PathLex 记录。",
    error_CONFLICT: "该操作与单元当前状态冲突，请刷新后重试。",
    error_INTERNAL_ERROR: "服务无法完成请求，请查看服务端日志后重试。",
    unitError_LLM_NOT_CONFIGURED: "请先配置 LLM API 密钥，再创建新单元。",
    unitError_PLAN_INFEASIBLE: "请求的机会槽位无法放入该有限图，请调整深度、间隔或机会次数。",
    unitError_GENERATION_FAILURE: "模型未返回完整且结构可用的故事图。",
    unitError_VERIFICATION_UNKNOWN: "至少一个教学机会尚无足够确定的验证结论。",
    unitError_COUNTEREXAMPLE: "仍有一条可达路径存在明确的词汇教学机会欠缺。",
    unitError_COMPILATION_FAILED: "编译意外停止，请检查服务端日志并用修订后的要求创建新单元。",
    unitError_REPAIR_FAILED: "修复操作意外停止，该单元已按 UNKNOWN 关闭。",
    operationalNotice: "此处审计仅检查一个生成单元的运行状态，不是方法改善学习的证据。",
  },
};

const state = {
  lang: localStorage.getItem("pathlex.language") === "zh" ? "zh" : "en",
  route: "home",
  activeUnit: null,
  session: null,
  targetCount: 1,
  nextTargetId: 1,
  teacherDraft: null,
  busy: false,
};

const app = document.querySelector("#app");
const toastRegion = document.querySelector("#toast-region");

function t(key, vars = {}) {
  let value = I18N[state.lang][key] ?? I18N.en[key] ?? key;
  Object.entries(vars).forEach(([name, replacement]) => {
    value = value.replaceAll(`{${name}}`, String(replacement));
  });
  return value;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatStory(value) {
  return escapeHtml(value)
    .replace(/\*\*([^*]+)\*\*/g, '<mark class="target-word">$1</mark>')
    .replace(/\n\n+/g, "</p><p>")
    .replace(/\n/g, "<br>");
}

function localized(value) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value[state.lang] ?? value.en ?? value.zh ?? "";
  }
  return value ?? "";
}

function splitList(value) {
  return String(value ?? "")
    .split(/[,;\n，；]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function numberValue(formData, name, fallback = 0) {
  const value = Number(formData.get(name));
  return Number.isFinite(value) ? value : fallback;
}

function unwrap(payload, key) {
  return payload?.[key] ?? payload;
}

function listFrom(payload) {
  if (Array.isArray(payload)) return payload;
  return payload?.items ?? payload?.units ?? payload?.stories ?? [];
}

async function api(path, options = {}, timeoutMs = 180000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...(options.headers ?? {}),
      },
      signal: controller.signal,
    });
    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : { message: await response.text() };
    if (!response.ok) {
      const serverError = payload?.error;
      const code = serverError && typeof serverError === "object" ? serverError.code : payload?.code;
      const translated = code ? I18N[state.lang][`error_${code}`] : "";
      const fallback = serverError && typeof serverError === "object"
        ? serverError.message
        : (payload?.message ?? serverError ?? payload?.detail);
      const message = translated || localized(fallback);
      const error = new Error(message || t("apiError"));
      error.status = response.status;
      error.code = code;
      throw error;
    }
    return payload;
  } catch (error) {
    if (error.name === "AbortError" || error instanceof TypeError) {
      throw new Error(t("networkError"));
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

function toast(message, tone = "success") {
  const element = document.createElement("div");
  element.className = `toast ${tone === "error" ? "error" : ""}`;
  element.setAttribute("role", tone === "error" ? "alert" : "status");
  element.textContent = message;
  toastRegion.append(element);
  window.setTimeout(() => element.remove(), 4800);
}

function setBusy(value) {
  state.busy = value;
  document.querySelectorAll("button, input, select, textarea").forEach((control) => {
    if (control.closest(".language-switch")) return;
    if (value) {
      control.dataset.wasDisabled = control.disabled ? "true" : "false";
      control.disabled = true;
    } else if (control.dataset.wasDisabled === "false") {
      control.disabled = false;
      delete control.dataset.wasDisabled;
    }
  });
}

function updateStaticLanguage() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.title = state.lang === "zh" ? "PathLex｜分支词汇故事" : "PathLex | Branch-aware vocabulary stories";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAria));
  });
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.language === state.lang));
  });
}

function currentRoute() {
  const raw = window.location.hash.replace(/^#\/?/, "").split("?")[0];
  return raw || "home";
}

function go(route) {
  if (currentRoute() === route) {
    renderRoute();
  } else {
    window.location.hash = route;
  }
}

function updateNav(route) {
  const group = route.startsWith("teacher")
    ? "teacher"
    : route.startsWith("library") || route.startsWith("play")
      ? "library"
      : "home";
  document.querySelectorAll("[data-route]").forEach((button) => {
    if (button.dataset.route === group) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
}

function loadingMarkup(key = "loading") {
  return `<div class="loading-state" role="status"><span class="loading-branch" aria-hidden="true"></span><span>${escapeHtml(t(key))}</span></div>`;
}

function errorMarkup(message) {
  return `<div class="error-panel" role="alert">${escapeHtml(message || t("apiError"))}</div>`;
}

function renderHome() {
  app.innerHTML = `
    <div class="page-shell">
      <section class="home-hero" aria-labelledby="home-title">
        <div class="hero-copy">
          <h1 id="home-title">${escapeHtml(t("homeTitle"))}</h1>
          <p>${escapeHtml(t("homeIntro"))}</p>
          <div class="hero-actions">
            <button class="primary-button" type="button" data-go="teacher">${escapeHtml(t("openStudio"))}</button>
            <button class="secondary-button" type="button" data-go="library">${escapeHtml(t("browseStories"))}</button>
          </div>
        </div>
        <div class="map-stage" role="img" aria-label="${escapeHtml(t("heroMapLabel"))}">
          <svg class="hero-map" viewBox="0 0 620 520" role="img" aria-hidden="true">
            <path class="branch-line" d="M62 260 C145 260 140 150 225 150 S312 80 388 80" />
            <path class="branch-line" d="M225 150 C320 150 305 232 397 232 S475 170 548 170" />
            <path class="branch-line" d="M62 260 C145 260 140 365 225 365 S315 300 399 300" />
            <path class="branch-line debt" d="M225 365 C318 365 313 438 401 438 S480 384 554 384" />
            <circle class="node" cx="62" cy="260" r="22" />
            <circle class="node target-node" cx="225" cy="150" r="25" />
            <circle class="node" cx="225" cy="365" r="25" />
            <circle class="node target-node" cx="397" cy="232" r="25" />
            <circle class="node" cx="399" cy="300" r="25" />
            <circle class="node" cx="388" cy="80" r="22" />
            <circle class="node" cx="548" cy="170" r="22" />
            <circle class="node" cx="554" cy="384" r="22" />
            <text x="28" y="307">${escapeHtml(t("mapStart"))}</text>
            <text x="183" y="116">${escapeHtml(t("mapExposure"))}</text>
            <text x="355" y="196">${escapeHtml(t("mapRetrieval"))}</text>
            <text x="378" y="480">${escapeHtml(t("mapDebt"))}</text>
          </svg>
          <p class="map-caption">${escapeHtml(t("mapCaption"))}</p>
        </div>
      </section>

      <section class="role-paths" aria-label="${escapeHtml(t("roleChoiceLabel"))}">
        <article class="role-path">
          <h2>${escapeHtml(t("teacherRole"))}</h2>
          <p>${escapeHtml(t("teacherRoleText"))}</p>
          <button class="text-button action-line" type="button" data-go="teacher">${escapeHtml(t("teacherRoleAction"))}</button>
        </article>
        <article class="role-path">
          <h2>${escapeHtml(t("studentRole"))}</h2>
          <p>${escapeHtml(t("studentRoleText"))}</p>
          <button class="text-button action-line" type="button" data-go="library">${escapeHtml(t("studentRoleAction"))}</button>
        </article>
      </section>
    </div>`;
  document.querySelectorAll("[data-go]").forEach((button) => {
    button.addEventListener("click", () => go(button.dataset.go));
  });
}

function targetEditor(index, target = {}) {
  const modes = target.mode_counts ?? target.modes ?? {};
  return `
    <article class="target-editor" data-target-index="${index}">
      <div class="target-editor-header">
        <span class="target-index" aria-label="${escapeHtml(t("targetNumber", { number: index + 1 }))}">${index + 1}</span>
        <button class="text-button remove-target" type="button" ${state.targetCount <= 1 ? "disabled" : ""}>${escapeHtml(t("removeTarget"))}</button>
      </div>
      <div class="field-grid">
        <div class="field">
          <label for="target-word-${index}">${escapeHtml(t("targetWord"))}</label>
          <input id="target-word-${index}" name="target_word_${index}" required autocomplete="off" placeholder="${escapeHtml(t("targetWordPlaceholder"))}" value="${escapeHtml(target.word ?? target.lemma ?? "")}" />
        </div>
        <div class="field">
          <label for="target-sense-${index}">${escapeHtml(t("sense"))}</label>
          <input id="target-sense-${index}" name="target_sense_${index}" required placeholder="${escapeHtml(t("sensePlaceholder"))}" value="${escapeHtml(target.sense ?? target.gloss ?? "")}" />
        </div>
        <div class="field">
          <label for="target-pos-${index}">${escapeHtml(t("partOfSpeech"))}</label>
          <select id="target-pos-${index}" name="target_pos_${index}">
            ${["verb", "noun", "adjective", "adverb", "other"].map((value) => `<option value="${value}" ${target.part_of_speech === value ? "selected" : ""}>${escapeHtml(t(`pos${value[0].toUpperCase()}${value.slice(1)}`))}</option>`).join("")}
          </select>
        </div>
        <div class="field">
          <label for="target-contexts-${index}">${escapeHtml(t("contexts"))}</label>
          <input id="target-contexts-${index}" name="target_contexts_${index}" placeholder="${escapeHtml(t("contextsPlaceholder"))}" value="${escapeHtml((target.contexts ?? []).join?.(", ") ?? target.contexts ?? "")}" />
        </div>
        <div class="field">
          <label for="target-phases-${index}">${escapeHtml(t("phases"))}</label>
          <input id="target-phases-${index}" name="target_phases_${index}" placeholder="${escapeHtml(t("phasesPlaceholder"))}" value="${escapeHtml((target.required_phases ?? []).join?.(", ") ?? target.required_phases ?? "")}" />
        </div>
        <div class="field wide">
          <label for="target-allowed-${index}">${escapeHtml(t("allowedCollocations"))}</label>
          <input id="target-allowed-${index}" name="target_allowed_${index}" placeholder="${escapeHtml(t("allowedPlaceholder"))}" value="${escapeHtml((target.allowed_collocations ?? []).join?.(", ") ?? target.allowed_collocations ?? "")}" />
        </div>
        <div class="field wide">
          <label for="target-forbidden-${index}">${escapeHtml(t("forbiddenCollocations"))}</label>
          <input id="target-forbidden-${index}" name="target_forbidden_${index}" placeholder="${escapeHtml(t("forbiddenPlaceholder"))}" value="${escapeHtml((target.forbidden_collocations ?? []).join?.(", ") ?? target.forbidden_collocations ?? "")}" />
        </div>
        <div class="field">
          <label for="target-positive-${index}">${escapeHtml(t("positiveExamples"))}</label>
          <textarea id="target-positive-${index}" name="target_positive_${index}" placeholder="${escapeHtml(t("positivePlaceholder"))}">${escapeHtml((target.positive_examples ?? []).join?.("\n") ?? target.positive_examples ?? "")}</textarea>
        </div>
        <div class="field">
          <label for="target-negative-${index}">${escapeHtml(t("negativeExamples"))}</label>
          <textarea id="target-negative-${index}" name="target_negative_${index}" placeholder="${escapeHtml(t("negativePlaceholder"))}">${escapeHtml((target.negative_examples ?? []).join?.("\n") ?? target.negative_examples ?? "")}</textarea>
        </div>
      </div>
      <div class="field-grid three">
        <div class="field">
          <label for="target-occurrences-${index}">${escapeHtml(t("occurrenceCount"))}</label>
          <input id="target-occurrences-${index}" name="target_occurrences_${index}" type="number" min="1" max="12" value="${Number(target.min_occurrences ?? 3)}" required />
        </div>
        <div class="field">
          <label for="target-min-gap-${index}">${escapeHtml(t("minGap"))}</label>
          <input id="target-min-gap-${index}" name="target_min_gap_${index}" type="number" min="0" max="8" value="${Number(target.min_gap ?? 0)}" />
        </div>
        <div class="field">
          <label for="target-max-gap-${index}">${escapeHtml(t("maxGap"))}</label>
          <input id="target-max-gap-${index}" name="target_max_gap_${index}" type="number" min="0" max="12" value="${Number(target.max_gap ?? 0)}" />
        </div>
        <div class="field">
          <label for="target-min-contexts-${index}">${escapeHtml(t("minContexts"))}</label>
          <input id="target-min-contexts-${index}" name="target_min_contexts_${index}" type="number" min="1" max="8" value="${Number(target.min_contexts ?? 1)}" />
        </div>
      </div>
      <div class="mode-fields">
        <div class="field">
          <label for="target-exposure-${index}">${escapeHtml(t("modeExposure"))}</label>
          <input id="target-exposure-${index}" name="target_exposure_${index}" type="number" min="0" max="12" value="${Number(modes.exposure ?? 1)}" />
        </div>
        <div class="field">
          <label for="target-judgment-${index}">${escapeHtml(t("modeJudgment"))}</label>
          <input id="target-judgment-${index}" name="target_judgment_${index}" type="number" min="0" max="12" value="${Number(modes.judgment ?? 0)}" />
        </div>
        <div class="field">
          <label for="target-retrieval-${index}">${escapeHtml(t("modeRetrieval"))}</label>
          <input id="target-retrieval-${index}" name="target_retrieval_${index}" type="number" min="0" max="12" value="${Number(modes.retrieval ?? 1)}" />
        </div>
      </div>
      <span class="hint">${escapeHtml(t("modesHint"))}</span>
      <p class="inline-error" hidden></p>
    </article>`;
}

function emptyAuditMarkup() {
  return `
    <div class="audit-empty">
      <svg class="empty-map" viewBox="0 0 320 170" aria-hidden="true">
        <path d="M24 85h70c42 0 34-48 79-48h74" fill="none" stroke="#78939a" stroke-width="2" stroke-dasharray="6 7" />
        <path d="M94 85c42 0 35 48 79 48h98" fill="none" stroke="#78939a" stroke-width="2" stroke-dasharray="6 7" />
        <circle cx="24" cy="85" r="11" fill="#fff" stroke="#103646" stroke-width="2" />
        <circle cx="173" cy="37" r="12" fill="#fff1b8" stroke="#a57300" stroke-width="2" />
        <circle cx="173" cy="133" r="12" fill="#fff" stroke="#103646" stroke-width="2" />
        <circle cx="271" cy="133" r="11" fill="#fff" stroke="#103646" stroke-width="2" />
      </svg>
      <h2>${escapeHtml(t("auditEmptyTitle"))}</h2>
      <p>${escapeHtml(t("auditEmptyText"))}</p>
    </div>`;
}

function draftFromStoredSpec(spec = {}) {
  return {
    title: spec.title ?? "",
    interface_language: spec.interface_language ?? state.lang,
    cefr_level: spec.cefr_level ?? "B1",
    theme: spec.theme ?? "",
    known_vocabulary: spec.known_vocabulary ?? [],
    base_vocabulary: spec.base_vocabulary ?? [],
    safety_notes: (spec.safety_constraints ?? []).join?.("; ") ?? spec.safety_constraints ?? "",
    graph: {
      depth: spec.depth ?? 4,
      branch_factor: spec.branch_factor ?? 2,
      max_paths: spec.max_paths ?? 32,
      common_prefix_opportunity_limit: spec.common_prefix_max_ratio ?? 0.5,
    },
    targets: (spec.targets ?? []).map((target) => ({
      word: target.lemma ?? target.word ?? "",
      sense: target.sense ?? "",
      part_of_speech: target.part_of_speech ?? "other",
      allowed_collocations: target.allowed_collocations ?? [],
      forbidden_collocations: target.forbidden_patterns ?? [],
      positive_examples: target.positive_examples ?? [],
      negative_examples: target.negative_examples ?? [],
      contexts: target.context_labels ?? ["general"],
      required_phases: target.required_phases ?? [],
      min_occurrences: target.min_occurrences ?? 3,
      min_gap: target.min_gap ?? 0,
      max_gap: target.max_gap ?? null,
      min_contexts: target.min_contexts ?? 1,
      mode_counts: target.mode_requirements ?? {},
    })),
  };
}

function renderTeacher(unit = state.activeUnit) {
  const draft = unit?.spec ? draftFromStoredSpec(unit.spec) : (state.teacherDraft ?? {});
  if (unit?.spec) state.teacherDraft = draft;
  const draftGraph = draft.graph ?? {};
  if (Array.isArray(draft.targets) && draft.targets.length) {
    state.targetCount = draft.targets.length;
  }
  state.nextTargetId = Math.max(state.nextTargetId, state.targetCount);
  app.innerHTML = `
    <div class="page-shell">
      <header class="page-heading">
        <h1>${escapeHtml(t("teacherTitle"))}</h1>
        <p>${escapeHtml(t("teacherIntro"))}</p>
      </header>
      <div class="teacher-layout">
        <form class="authoring-sheet" id="story-form" novalidate>
          <section class="sheet-section">
            <div class="section-heading"><div><h2>${escapeHtml(t("storyBrief"))}</h2><p>${escapeHtml(t("storyBriefHelp"))}</p></div></div>
            <div class="field-grid">
              <div class="field">
                <label for="story-title">${escapeHtml(t("titleLabel"))}</label>
                <input id="story-title" name="title" required maxlength="120" placeholder="${escapeHtml(t("titlePlaceholder"))}" value="${escapeHtml(draft.title ?? "")}" />
              </div>
              <div class="field">
                <label for="cefr-level">${escapeHtml(t("cefrLabel"))}</label>
                <select id="cefr-level" name="cefr_level">${["A1", "A2", "B1", "B2", "C1"].map((level) => `<option ${String(draft.cefr_level ?? "B1") === level ? "selected" : ""}>${level}</option>`).join("")}</select>
              </div>
              <div class="field wide">
                <label for="story-theme">${escapeHtml(t("themeLabel"))}</label>
                <input id="story-theme" name="theme" required maxlength="300" placeholder="${escapeHtml(t("themePlaceholder"))}" value="${escapeHtml(draft.theme ?? "")}" />
              </div>
              <div class="field">
                <label for="known-vocab">${escapeHtml(t("knownLabel"))}</label>
                <textarea id="known-vocab" name="known_vocabulary" placeholder="${escapeHtml(t("knownPlaceholder"))}">${escapeHtml((draft.known_vocabulary ?? []).join?.(", ") ?? draft.known_vocabulary ?? "")}</textarea>
                <span class="hint">${escapeHtml(t("knownHint"))}</span>
              </div>
              <div class="field">
                <label for="base-vocab">${escapeHtml(t("baseLabel"))}</label>
                <textarea id="base-vocab" name="base_vocabulary" placeholder="${escapeHtml(t("basePlaceholder"))}">${escapeHtml((draft.base_vocabulary ?? []).join?.(", ") ?? draft.base_vocabulary ?? "")}</textarea>
                <span class="hint">${escapeHtml(t("baseHint"))}</span>
              </div>
              <div class="field wide">
                <label for="safety-notes">${escapeHtml(t("safetyLabel"))}</label>
                <textarea id="safety-notes" name="safety_notes" placeholder="${escapeHtml(t("safetyPlaceholder"))}">${escapeHtml(draft.safety_notes ?? "")}</textarea>
              </div>
            </div>
          </section>

          <section class="sheet-section">
            <div class="section-heading"><div><h2>${escapeHtml(t("topology"))}</h2><p>${escapeHtml(t("topologyHelp"))}</p></div></div>
            <div class="field-grid three">
              <div class="field"><label for="story-depth">${escapeHtml(t("depthLabel"))}</label><input id="story-depth" name="depth" type="number" min="3" max="9" value="${Number(draftGraph.depth ?? 4)}" /></div>
              <div class="field"><label for="branch-factor">${escapeHtml(t("branchLabel"))}</label><input id="branch-factor" name="branch_factor" type="number" min="2" max="3" value="${Number(draftGraph.branch_factor ?? 2)}" /></div>
              <div class="field"><label for="max-paths">${escapeHtml(t("maxPathsLabel"))}</label><input id="max-paths" name="max_paths" type="number" min="2" max="128" value="${Number(draftGraph.max_paths ?? 32)}" /></div>
              <div class="field"><label for="prefix-limit">${escapeHtml(t("commonPrefixLabel"))}</label><input id="prefix-limit" name="common_prefix_limit" type="number" min="0" max="1" step="0.05" value="${Number(draftGraph.common_prefix_opportunity_limit ?? 0.5)}" /><span class="hint">${escapeHtml(t("commonPrefixHint"))}</span></div>
            </div>
          </section>

          <section class="sheet-section">
            <div class="section-heading">
              <div><h2>${escapeHtml(t("targets"))}</h2><p>${escapeHtml(t("targetsHelp"))}</p></div>
              <button class="secondary-button" id="add-target" type="button">${escapeHtml(t("addTarget"))}</button>
            </div>
            <div class="target-list" id="target-list">${Array.from({ length: state.targetCount }, (_, index) => targetEditor(index, draft.targets?.[index] ?? {})).join("")}</div>
          </section>

          <section class="sheet-section form-actions">
            <p class="form-note">${escapeHtml(t("compileNote"))}</p>
            <button class="primary-button" id="compile-button" type="submit">${escapeHtml(t("compileStory"))}</button>
          </section>

          <section class="sheet-section">
            <div class="section-heading"><div><h2>${escapeHtml(t("existingUnits"))}</h2></div></div>
            <div id="teacher-unit-list">${loadingMarkup()}</div>
          </section>
        </form>
        <aside class="audit-rail" id="audit-rail" aria-label="${escapeHtml(t("auditStatus"))}">
          ${unit ? auditMarkup(unit) : emptyAuditMarkup()}
        </aside>
      </div>
    </div>`;
  bindTeacherEvents();
  loadTeacherUnits();
}

function bindTeacherEvents() {
  const list = document.querySelector("#target-list");
  const add = document.querySelector("#add-target");
  add?.addEventListener("click", () => {
    state.targetCount += 1;
    const targetId = state.nextTargetId;
    state.nextTargetId += 1;
    list.insertAdjacentHTML("beforeend", targetEditor(targetId));
    renumberTargets();
    bindRemoveTargets();
    list.lastElementChild?.querySelector("input")?.focus();
  });
  bindRemoveTargets();
  document.querySelector("#story-form")?.addEventListener("submit", submitStory);
  bindAuditEvents();
}

function bindRemoveTargets() {
  document.querySelectorAll(".remove-target").forEach((button) => {
    button.disabled = state.targetCount <= 1;
    button.onclick = () => {
      if (state.targetCount <= 1) return;
      button.closest(".target-editor")?.remove();
      state.targetCount -= 1;
      renumberTargets();
      bindRemoveTargets();
    };
  });
}

function renumberTargets() {
  document.querySelectorAll(".target-editor").forEach((editor, index) => {
    editor.querySelector(".target-index").textContent = String(index + 1);
    editor.querySelector(".target-index").setAttribute("aria-label", t("targetNumber", { number: index + 1 }));
  });
}

function buildSpec(form) {
  const formData = new FormData(form);
  const depth = numberValue(formData, "depth", 4);
  const branchFactor = numberValue(formData, "branch_factor", 2);
  const maxPaths = numberValue(formData, "max_paths", 32);
  const targets = [];
  let validationKey = "";
  document.querySelectorAll(".target-editor").forEach((editor, listIndex) => {
    const originalIndex = Number(editor.dataset.targetIndex ?? listIndex);
    const read = (suffix) => formData.get(`target_${suffix}_${originalIndex}`) ?? "";
    const minOccurrences = Number(read("occurrences"));
    const minGap = Number(read("min_gap"));
    const maxGap = Number(read("max_gap"));
    const exposure = Number(read("exposure"));
    const judgment = Number(read("judgment"));
    const retrieval = Number(read("retrieval"));
    if (!String(read("word")).trim() || !String(read("sense")).trim() || minOccurrences < 1) validationKey ||= "targetError";
    if (maxGap > 0 && maxGap < minGap) validationKey ||= "gapError";
    if (exposure + judgment + retrieval > minOccurrences) validationKey ||= "modeError";
    const contexts = splitList(read("contexts"));
    const minContexts = Number(read("min_contexts")) || 1;
    const requiredPhases = splitList(read("phases")).map((value) => value.toLowerCase());
    if (minContexts > Math.max(1, contexts.length)) validationKey ||= "contextCountError";
    if (requiredPhases.some((value) => !["opening", "middle", "ending"].includes(value))) validationKey ||= "phaseError";
    targets.push({
      word: String(read("word")).trim(),
      sense: String(read("sense")).trim(),
      part_of_speech: String(read("pos")),
      allowed_collocations: splitList(read("allowed")),
      forbidden_collocations: splitList(read("forbidden")),
      positive_examples: splitList(read("positive")),
      negative_examples: splitList(read("negative")),
      contexts,
      required_phases: requiredPhases,
      min_occurrences: minOccurrences,
      min_gap: minGap,
      max_gap: maxGap || null,
      min_contexts: minContexts,
      mode_counts: { exposure, judgment, retrieval },
    });
  });
  if (Math.pow(branchFactor, Math.max(1, depth - 1)) > maxPaths) validationKey ||= "topologyError";
  if (!String(formData.get("title") ?? "").trim() || !String(formData.get("theme") ?? "").trim()) validationKey ||= "requiredError";
  return {
    validationKey,
    payload: {
      title: String(formData.get("title")).trim(),
      interface_language: state.lang,
      cefr_level: String(formData.get("cefr_level")),
      theme: String(formData.get("theme")).trim(),
      known_vocabulary: splitList(formData.get("known_vocabulary")),
      base_vocabulary: splitList(formData.get("base_vocabulary")),
      safety_notes: String(formData.get("safety_notes") ?? "").trim(),
      graph: {
        depth,
        branch_factor: branchFactor,
        max_paths: maxPaths,
        common_prefix_opportunity_limit: numberValue(formData, "common_prefix_limit", 0.5),
      },
      targets,
    },
  };
}

async function submitStory(event) {
  event.preventDefault();
  const { validationKey, payload } = buildSpec(event.currentTarget);
  if (validationKey) {
    toast(t(validationKey), "error");
    return;
  }
  setBusy(true);
  const button = document.querySelector("#compile-button");
  if (button) button.textContent = t("compiling");
  try {
    const result = await api("/api/units", { method: "POST", body: JSON.stringify(payload) });
    state.activeUnit = unwrap(result, "unit");
    state.teacherDraft = payload;
    if (!state.activeUnit?.id) throw new Error(t("apiError"));
    go(`teacher/${encodeURIComponent(state.activeUnit.id)}`);
  } catch (error) {
    toast(error.message || t("apiError"), "error");
  } finally {
    setBusy(false);
    if (button) button.textContent = t("compileStory");
  }
}

async function loadTeacherUnits() {
  const host = document.querySelector("#teacher-unit-list");
  if (!host) return;
  try {
    const units = listFrom(await api("/api/units", {}, 30000));
    if (!units.length) {
      host.innerHTML = `<p>${escapeHtml(t("noSavedUnits"))}</p>`;
      return;
    }
    host.innerHTML = `<ul class="ledger-list">${units.map((unit) => `<li><span><strong>${escapeHtml(unit.title ?? unit.spec?.title ?? unit.id)}</strong><br><small>${escapeHtml(statusText(unit.status))}</small></span><button class="text-button load-unit" data-unit-id="${escapeHtml(unit.id)}" type="button">${escapeHtml(t("loadUnit"))}</button></li>`).join("")}</ul>`;
    host.querySelectorAll(".load-unit").forEach((button) => {
      button.addEventListener("click", () => go(`teacher/${encodeURIComponent(button.dataset.unitId)}`));
    });
  } catch (error) {
    host.innerHTML = errorMarkup(error.message);
  }
}

function statusText(status) {
  return t(`status_${normalizeStatus(status)}`);
}

function normalizeStatus(status) {
  const raw = String(status ?? "DRAFT").toUpperCase();
  if (raw.includes("PLAN-INFEASIBLE") || raw.includes("PLAN_INFEASIBLE") || raw.includes("UNSAT")) {
    return "PLAN_INFEASIBLE";
  }
  return raw.replaceAll("-", "_").replace(/[^A-Z_]/g, "");
}

function statusTone(status) {
  const value = normalizeStatus(status);
  if (value === "VERIFIED") return "good";
  if (["COUNTEREXAMPLE", "PLAN_FEASIBLE", "GENERATING", "VERIFYING", "DRAFT"].includes(value)) return "warn";
  return "bad";
}

function unitGraph(unit) {
  const graph = unit.graph ?? unit.story_graph ?? {};
  let nodes = graph.nodes ?? unit.nodes ?? [];
  if (!Array.isArray(nodes)) nodes = Object.entries(nodes).map(([id, node]) => ({ id, ...node }));
  nodes = nodes.map((node, index) => ({ id: String(node.id ?? node.node_id ?? `n${index}`), ...node }));
  let edges = graph.edges ?? unit.edges ?? [];
  if (!Array.isArray(edges) && edges && typeof edges === "object") {
    edges = Object.entries(edges).flatMap(([source, targets]) =>
      (Array.isArray(targets) ? targets : []).map((target, index) => ({
        source,
        target: typeof target === "object" ? (target.target ?? target.next_id) : target,
        id: `${source}-${index}`,
      })),
    );
  }
  if (!edges.length) {
    edges = nodes.flatMap((node) => {
      const choices = node.choices ?? node.options ?? [];
      return choices.map((choice, index) => ({
        source: node.id,
        target: choice.next_node_id ?? choice.next_id ?? choice.target ?? choice.next,
        id: choice.id ?? `${node.id}-${index}`,
      }));
    });
  }
  edges = edges.map((edge, index) => ({
    id: String(edge.id ?? `e${index}`),
    source: String(edge.source ?? edge.from ?? edge.parent_id ?? ""),
    target: String(edge.target ?? edge.to ?? edge.child_id ?? ""),
  })).filter((edge) => edge.source && edge.target);
  const rootId = String(graph.root_id ?? unit.root_id ?? nodes[0]?.id ?? "");
  return { nodes, edges, rootId };
}

function graphSvg(unit) {
  const { nodes, edges, rootId } = unitGraph(unit);
  if (!nodes.length) return "";
  const nodeMap = new Map(nodes.map((node) => [node.id, node]));
  const depth = new Map([[rootId, 0]]);
  for (let pass = 0; pass < nodes.length; pass += 1) {
    edges.forEach((edge) => {
      if (depth.has(edge.source)) depth.set(edge.target, Math.max(depth.get(edge.target) ?? 0, depth.get(edge.source) + 1));
    });
  }
  nodes.forEach((node) => depth.set(node.id, Number(node.depth ?? depth.get(node.id) ?? 0)));
  const groups = new Map();
  nodes.forEach((node) => {
    const d = depth.get(node.id) ?? 0;
    if (!groups.has(d)) groups.set(d, []);
    groups.get(d).push(node);
  });
  const maxDepth = Math.max(...groups.keys());
  const maxRows = Math.max(...[...groups.values()].map((group) => group.length));
  const width = Math.max(420, (maxDepth + 1) * 145);
  const height = Math.max(280, maxRows * 74 + 60);
  const position = new Map();
  groups.forEach((group, d) => {
    group.forEach((node, row) => {
      position.set(node.id, {
        x: 52 + d * ((width - 104) / Math.max(1, maxDepth)),
        y: ((row + 1) * height) / (group.length + 1),
      });
    });
  });
  const worstPath = unit.audit?.worst_path ?? unit.worst_path ?? [];
  const worstEdges = new Set(worstPath.slice(0, -1).map((id, index) => `${id}|${worstPath[index + 1]}`));
  const worstNodes = new Set(worstPath.map(String));
  return `<svg class="graph-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(t("branchGraphLabel"))}">
    ${edges.map((edge) => {
      const start = position.get(edge.source);
      const end = position.get(edge.target);
      if (!start || !end) return "";
      return `<line class="edge ${worstEdges.has(`${edge.source}|${edge.target}`) ? "worst" : ""}" x1="${start.x}" y1="${start.y}" x2="${end.x}" y2="${end.y}" />`;
    }).join("")}
    ${nodes.map((node) => {
      const point = position.get(node.id);
      const hasSlot = (node.slots ?? node.planned_slots ?? node.opportunity_slots ?? []).length > 0;
      return `<g><circle class="graph-node ${hasSlot ? "has-slot" : ""} ${worstNodes.has(node.id) ? "worst" : ""}" cx="${point.x}" cy="${point.y}" r="18" /><text x="${point.x}" y="${point.y + 33}" text-anchor="middle">${escapeHtml(node.label ?? node.id).slice(0, 16)}</text></g>`;
    }).join("")}
  </svg>`;
}

function metricValue(value, kind = "number") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  if (kind === "percent") return `${Math.round(Number(value) * 100)}%`;
  return String(value);
}

function unitErrorMessage(error) {
  if (!error) return "";
  const key = `unitError_${error.code ?? ""}`;
  return I18N[state.lang][key] ?? t("apiError");
}

function auditMarkup(unit) {
  const audit = unit.audit ?? unit.audit_report ?? {};
  const graph = unitGraph(unit);
  const status = normalizeStatus(unit.status ?? audit.status ?? "DRAFT");
  const debts = audit.debts ?? audit.worst_path_debts ?? unit.debts ?? [];
  const worstCoverage = audit.worst_path_coverage ?? audit.worst_coverage ?? audit.wpc;
  const passRate = audit.path_pass_rate ?? audit.path_pass_ratio ?? audit.all_path_pass_rate;
  const pathCount = audit.path_count ?? audit.reachable_terminal_paths ?? unit.path_count ?? null;
  const calls = unit.budget?.calls ?? unit.usage?.calls ?? unit.runtime?.budget?.used?.calls ?? audit.model_calls;
  const isPublished = Boolean(unit.published ?? unit.is_published);
  const reasonCodes = audit.plan_certificate?.reason_codes ?? [];
  return `
    <div class="status-band" data-tone="${statusTone(status)}">
      <span>${escapeHtml(t("auditStatus"))}</span>
      <strong class="status-code">${escapeHtml(statusText(status))}</strong>
    </div>
    <div class="audit-content">
      <div class="audit-title-row"><div><h2>${escapeHtml(unit.title ?? unit.spec?.title ?? unit.id)}</h2><p class="unit-meta">${escapeHtml(unit.id ?? "")}</p></div>${isPublished ? `<strong>${escapeHtml(t("published"))}</strong>` : ""}</div>
      ${unit.error ? `<div class="error-panel" role="status"><strong>${escapeHtml(unit.error.code ?? "ERROR")}</strong><p>${escapeHtml(unitErrorMessage(unit.error))}</p></div>` : ""}
      ${reasonCodes.length ? `<p class="unit-meta"><strong>${escapeHtml(t("auditReasonCodes"))}:</strong> ${escapeHtml(reasonCodes.join(", "))}</p>` : ""}
    <div class="graph-frame">${graphSvg(unit) || `<div class="audit-empty"><p>${escapeHtml(t("auditEmptyText"))}</p></div>`}</div>
      <div class="audit-measures">
        <div class="audit-measure"><span>${escapeHtml(t("auditWorstCoverage"))}</span><strong>${metricValue(worstCoverage, "percent")}</strong></div>
        <div class="audit-measure"><span>${escapeHtml(t("auditPathPass"))}</span><strong>${metricValue(passRate, "percent")}</strong></div>
        <div class="audit-measure"><span>${escapeHtml(t("auditPaths"))}</span><strong>${metricValue(pathCount ?? Math.max(0, graph.nodes.filter((node) => !(graph.edges.some((edge) => edge.source === node.id))).length))}</strong></div>
        <div class="audit-measure"><span>${escapeHtml(t("auditCalls"))}</span><strong>${metricValue(calls)}</strong></div>
      </div>
      <h3>${escapeHtml(t("auditDebts"))}</h3>
      ${debts.length ? `<ul class="debt-list">${debts.slice(0, 12).map((debt) => `<li><span>${escapeHtml(debt.word ?? debt.lemma ?? debt.target ?? debt.target_id ?? debt.constraint ?? "")}</span><small>${escapeHtml(debt.reason ?? debt.requirement ?? debt.missing ?? debt.kind ?? debt.type ?? "")}</small></li>`).join("")}</ul>` : `<p>${escapeHtml(t("noDebts"))}</p>`}
      <p class="unit-meta">${escapeHtml(t("operationalNotice"))}</p>
      <div class="audit-actions">
        <button class="secondary-button" id="refresh-unit" data-unit-id="${escapeHtml(unit.id)}" type="button">${escapeHtml(t("refresh"))}</button>
        <button class="secondary-button" id="repair-unit" data-unit-id="${escapeHtml(unit.id)}" type="button" ${status !== "COUNTEREXAMPLE" ? "disabled" : ""}>${escapeHtml(t("repair"))}</button>
        <button class="primary-button" id="publish-unit" data-unit-id="${escapeHtml(unit.id)}" type="button" ${status !== "VERIFIED" || isPublished ? "disabled" : ""}>${escapeHtml(isPublished ? t("published") : t("publish"))}</button>
        <button class="text-button" id="export-unit" type="button">${escapeHtml(t("exportJson"))}</button>
      </div>
      ${status !== "VERIFIED" ? `<p class="unit-meta">${escapeHtml(t("publishGate"))}</p>` : ""}
    </div>`;
}

function bindAuditEvents() {
  document.querySelector("#refresh-unit")?.addEventListener("click", (event) => loadTeacherUnit(event.currentTarget.dataset.unitId));
  document.querySelector("#repair-unit")?.addEventListener("click", repairUnit);
  document.querySelector("#publish-unit")?.addEventListener("click", publishUnit);
  document.querySelector("#export-unit")?.addEventListener("click", exportUnit);
}

async function loadTeacherUnit(id, rerender = true) {
  try {
    const result = await api(`/api/units/${encodeURIComponent(id)}`);
    state.activeUnit = unwrap(result, "unit");
    if (rerender) renderTeacher(state.activeUnit);
  } catch (error) {
    if (rerender) app.innerHTML = `<div class="page-shell">${errorMarkup(error.status === 404 ? t("unitNotFound") : error.message)}</div>`;
  }
}

async function repairUnit(event) {
  const id = event.currentTarget.dataset.unitId;
  event.currentTarget.textContent = t("repairing");
  setBusy(true);
  try {
    const result = await api(`/api/units/${encodeURIComponent(id)}/repair`, {
      method: "POST",
      body: JSON.stringify({ interface_language: state.lang }),
    });
    state.activeUnit = unwrap(result, "unit");
    toast(t("repairedToast"));
    renderTeacher(state.activeUnit);
  } catch (error) {
    toast(error.message || t("apiError"), "error");
  } finally {
    setBusy(false);
  }
}

async function publishUnit(event) {
  const id = event.currentTarget.dataset.unitId;
  setBusy(true);
  try {
    const result = await api(`/api/units/${encodeURIComponent(id)}/publish`, {
      method: "POST",
      body: JSON.stringify({ interface_language: state.lang }),
    });
    state.activeUnit = unwrap(result, "unit");
    toast(t("publishedToast"));
    renderTeacher(state.activeUnit);
  } catch (error) {
    toast(error.message || t("apiError"), "error");
  } finally {
    setBusy(false);
  }
}

function exportUnit() {
  if (!state.activeUnit) return;
  const blob = new Blob([JSON.stringify(state.activeUnit, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `pathlex-${state.activeUnit.id ?? "unit"}.json`;
  link.click();
  URL.revokeObjectURL(url);
  toast(t("exportedToast"));
}

async function renderLibrary() {
  app.innerHTML = `<div class="page-shell"><header class="page-heading"><h1>${escapeHtml(t("libraryTitle"))}</h1><p>${escapeHtml(t("libraryIntro"))}</p></header>${loadingMarkup("libraryLoading")}</div>`;
  try {
    const units = listFrom(await api("/api/library", {}, 30000));
    if (!units.length) {
      app.innerHTML = `<div class="page-shell"><header class="page-heading"><h1>${escapeHtml(t("libraryTitle"))}</h1><p>${escapeHtml(t("libraryIntro"))}</p></header><div class="empty-state"><h2>${escapeHtml(t("libraryEmptyTitle"))}</h2><p>${escapeHtml(t("libraryEmptyText"))}</p><button class="primary-button" id="empty-go-teacher" type="button">${escapeHtml(t("goTeacher"))}</button></div></div>`;
      document.querySelector("#empty-go-teacher")?.addEventListener("click", () => go("teacher"));
      return;
    }
    app.innerHTML = `<div class="page-shell"><header class="page-heading"><h1>${escapeHtml(t("libraryTitle"))}</h1><p>${escapeHtml(t("libraryIntro"))}</p></header><div class="library-grid">${units.map(storyTicket).join("")}</div></div>`;
    document.querySelectorAll(".story-start").forEach((button) => button.addEventListener("click", startSession));
  } catch (error) {
    app.innerHTML = `<div class="page-shell"><header class="page-heading"><h1>${escapeHtml(t("libraryTitle"))}</h1></header>${errorMarkup(error.message)}</div>`;
  }
}

function storyTicket(unit) {
  const targets = unit.targets ?? unit.spec?.targets ?? [];
  const pathCount = unit.audit?.path_count ?? unit.path_count ?? "—";
  return `<article class="story-ticket">
    <div class="ticket-meta"><span>${escapeHtml(t("cefrMeta", { level: unit.cefr_level ?? unit.spec?.cefr_level ?? "—" }))}</span><span>${escapeHtml(t("targetMeta", { count: targets.length }))}</span><span>${escapeHtml(t("pathMeta", { count: pathCount }))}</span></div>
    <h2>${escapeHtml(unit.title ?? unit.spec?.title ?? unit.id)}</h2>
    <p>${escapeHtml(unit.theme ?? unit.spec?.theme ?? "")}</p>
    <button class="text-button play-label story-start" type="button" data-unit-id="${escapeHtml(unit.id)}">${escapeHtml(t("playStory"))}</button>
  </article>`;
}

async function startSession(event) {
  const unitId = event.currentTarget.dataset.unitId;
  app.innerHTML = `<div class="page-shell">${loadingMarkup("startingStory")}</div>`;
  try {
    const result = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ unit_id: unitId, interface_language: state.lang }),
    }, 30000);
    state.session = unwrap(result, "session");
    if (!state.session?.id) throw new Error(t("apiError"));
    go(`play/${encodeURIComponent(state.session.id)}`);
  } catch (error) {
    toast(error.message || t("apiError"), "error");
    go("library");
  }
}

function currentNode(session) {
  return session.current_node ?? session.node ?? session.current ?? {};
}

function sessionProgress(session) {
  if (typeof session.progress === "number") return Math.max(0, Math.min(1, session.progress));
  const current = Number(session.depth ?? session.step ?? session.progress?.depth ?? session.path?.length ?? 1);
  const total = Number(session.total_depth ?? session.max_steps ?? session.total_steps ?? session.progress?.max_depth ?? Math.max(current, 1));
  return Math.max(0, Math.min(1, current / Math.max(total, 1)));
}

function retrievalFor(node) {
  const activity = node.retrieval ?? (node.activity?.type === "retrieval" ? node.activity : null);
  if (!activity) return null;
  return {
    ...activity,
    prompt: localized(activity.prompt ?? activity.question ?? { en: activity.prompt_en, zh: activity.prompt_zh }),
    answered: Boolean(activity.answered ?? node.answer_recorded),
  };
}

function choicesFor(node) {
  return (node.choices ?? node.options ?? []).map((choice, index) => ({
    id: String(choice.id ?? choice.choice_id ?? index),
    next_node_id: choice.next_node_id ?? choice.target ?? choice.next,
    label: (() => {
      const value = choice.label ?? choice.text ?? { en: choice.label_en, zh: choice.label_zh };
      return value && typeof value === "object" ? (value.en ?? value[state.lang] ?? value.zh ?? "") : value;
    })(),
  }));
}

function renderPlayer(session) {
  if (session.complete ?? session.completed) {
    renderCompletion(session);
    return;
  }
  const node = currentNode(session);
  const retrieval = retrievalFor(node);
  const choices = choicesFor(node);
  const storyValue = node.text ?? node.story_text ?? node.body ?? "";
  const storyText = storyValue && typeof storyValue === "object"
    ? (storyValue.en ?? storyValue[state.lang] ?? "")
    : storyValue;
  const progress = sessionProgress(session);
  const current = Number(session.step ?? session.path?.length ?? Math.max(1, Math.round(progress * 10)));
  const total = Number(session.total_steps ?? session.total_depth ?? Math.max(current, 1));
  const feedback = localized(session.last_feedback ?? node.feedback_visible ?? (retrieval?.answered ? retrieval?.feedback : ""));
  const support = localized(node.support ?? "");
  const terminal = Boolean(node.terminal || !choices.length);
  const retrievalPending = Boolean(retrieval && !retrieval.answered);
  app.innerHTML = `<div class="player-shell">
    <div class="path-ribbon"><button class="text-button" id="back-library" type="button">${escapeHtml(t("backLibrary"))}</button><progress class="path-progress" max="100" value="${Math.round(progress * 100)}" aria-label="${escapeHtml(t("storyProgress", { current, total }))}"></progress><p>${escapeHtml(t("storyProgress", { current, total }))}</p></div>
    <article class="story-page">
      <header class="story-heading"><h1>${escapeHtml(session.unit_title ?? session.title ?? "PathLex")}</h1><span>${escapeHtml(session.cefr_level ?? "")}</span></header>
      <div class="story-text"><p>${formatStory(storyText)}</p></div>
      ${support ? `<aside class="support-note"><strong>${escapeHtml(t("supportTitle"))}</strong><p>${escapeHtml(support)}</p></aside>` : ""}
      ${retrieval ? `<section class="retrieval-panel"><h2>${escapeHtml(t("retrievalTitle"))}</h2><p>${escapeHtml(retrieval.prompt ?? "")}</p>${retrieval.answered ? "" : `<form class="answer-row" id="answer-form"><input name="answer" autocomplete="off" placeholder="${escapeHtml(t("retrievalPlaceholder"))}" aria-label="${escapeHtml(t("retrievalPlaceholder"))}" /><button class="primary-button" type="submit">${escapeHtml(t("checkAnswer"))}</button></form>`}${feedback ? `<div class="feedback-note ${session.last_answer_correct === false ? "is-correction" : ""}" role="status"><strong>${escapeHtml(t("feedbackLabel"))}</strong><p>${escapeHtml(feedback)}</p><small>${escapeHtml(t("answerRecorded"))}</small></div>` : ""}</section>` : ""}
      ${terminal
        ? `<section class="choice-field"><button class="primary-button" id="finish-story" type="button" ${retrievalPending ? "disabled" : ""}>${escapeHtml(t("finishEnding"))}</button>${retrievalPending ? `<p>${escapeHtml(t("choiceLocked"))}</p>` : ""}</section>`
        : `<section class="choice-field"><h2>${escapeHtml(t("chooseNext"))}</h2>${retrievalPending ? `<p>${escapeHtml(t("choiceLocked"))}</p>` : ""}<div class="choice-list">${choices.map((choice, index) => `<button class="choice-button" type="button" data-choice-id="${escapeHtml(choice.id)}" data-next-node-id="${escapeHtml(choice.next_node_id ?? "")}" ${retrievalPending ? "disabled" : ""}><span class="choice-letter">${String.fromCharCode(65 + index)}</span><span>${escapeHtml(choice.label)}</span></button>`).join("")}</div></section>`}
    </article>
  </div>`;
  document.querySelector("#back-library")?.addEventListener("click", () => go("library"));
  document.querySelector("#answer-form")?.addEventListener("submit", submitAnswer);
  document.querySelectorAll(".choice-button").forEach((button) => button.addEventListener("click", chooseBranch));
  document.querySelector("#finish-story")?.addEventListener("click", finishStory);
}

async function loadSession(id) {
  app.innerHTML = `<div class="player-shell">${loadingMarkup()}</div>`;
  try {
    const result = await api(`/api/sessions/${encodeURIComponent(id)}`, {}, 30000);
    state.session = unwrap(result, "session");
    renderPlayer(state.session);
  } catch (error) {
    app.innerHTML = `<div class="page-shell">${errorMarkup(error.status === 404 ? t("sessionNotFound") : error.message)}</div>`;
  }
}

async function submitAnswer(event) {
  event.preventDefault();
  const answer = new FormData(event.currentTarget).get("answer")?.trim();
  if (!answer) {
    toast(t("answerRequired"), "error");
    return;
  }
  setBusy(true);
  try {
    const result = await api(`/api/sessions/${encodeURIComponent(state.session.id)}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer, interface_language: state.lang }),
    }, 30000);
    state.session = unwrap(result, "session");
    if (result?.feedback && !state.session.last_feedback) state.session.last_feedback = result.feedback;
    if (result?.correct !== undefined && state.session.last_answer_correct === undefined) state.session.last_answer_correct = result.correct;
    renderPlayer(state.session);
  } catch (error) {
    toast(error.message || t("apiError"), "error");
  } finally {
    setBusy(false);
  }
}

async function chooseBranch(event) {
  const button = event.currentTarget;
  setBusy(true);
  try {
    const result = await api(`/api/sessions/${encodeURIComponent(state.session.id)}/choose`, {
      method: "POST",
      body: JSON.stringify({
        choice_id: button.dataset.choiceId,
        next_node_id: button.dataset.nextNodeId || null,
        interface_language: state.lang,
      }),
    }, 30000);
    state.session = unwrap(result, "session");
    renderPlayer(state.session);
    document.querySelector(".story-page")?.focus?.();
  } catch (error) {
    toast(error.message || t("apiError"), "error");
  } finally {
    setBusy(false);
  }
}

async function finishStory(event) {
  event.currentTarget.textContent = t("finishingEnding");
  setBusy(true);
  try {
    const result = await api(`/api/sessions/${encodeURIComponent(state.session.id)}/complete`, {
      method: "POST",
      body: JSON.stringify({ interface_language: state.lang }),
    }, 30000);
    state.session = unwrap(result, "session");
    renderPlayer(state.session);
  } catch (error) {
    toast(error.message || t("apiError"), "error");
  } finally {
    setBusy(false);
  }
}

function renderCompletion(session) {
  app.innerHTML = `<div class="player-shell"><section class="completion-panel">
    <svg class="completion-branch" viewBox="0 0 150 82" aria-hidden="true"><path d="M8 42h52c25 0 21-28 47-28h35M60 42c25 0 21 28 47 28h35" fill="none" stroke="#176b5b" stroke-width="3" stroke-linecap="round" /><circle cx="142" cy="14" r="6" fill="#f3c245" stroke="#103646" /><circle cx="142" cy="70" r="6" fill="#fff" stroke="#103646" /></svg>
    <h1>${escapeHtml(t("journeyComplete"))}</h1><p>${escapeHtml(t("completeText"))}</p>
    <div class="hero-actions"><button class="primary-button" id="complete-library" type="button">${escapeHtml(t("readAnother"))}</button><button class="secondary-button" id="complete-replay" data-unit-id="${escapeHtml(session.unit_id ?? "")}" type="button">${escapeHtml(t("replay"))}</button></div>
  </section></div>`;
  document.querySelector("#complete-library")?.addEventListener("click", () => go("library"));
  document.querySelector("#complete-replay")?.addEventListener("click", (event) => startSession({ currentTarget: { dataset: { unitId: event.currentTarget.dataset.unitId } } }));
}

async function renderRoute() {
  const route = currentRoute();
  state.route = route;
  updateStaticLanguage();
  updateNav(route);
  if (route === "home") {
    renderHome();
    return;
  }
  if (route === "teacher") {
    state.activeUnit = null;
    renderTeacher();
    return;
  }
  if (route.startsWith("teacher/")) {
    const id = decodeURIComponent(route.slice("teacher/".length));
    if (state.activeUnit?.id === id) renderTeacher(state.activeUnit);
    else {
      app.innerHTML = `<div class="page-shell">${loadingMarkup()}</div>`;
      await loadTeacherUnit(id);
    }
    return;
  }
  if (route === "library") {
    await renderLibrary();
    return;
  }
  if (route.startsWith("play/")) {
    const id = decodeURIComponent(route.slice("play/".length));
    if (state.session?.id === id) renderPlayer(state.session);
    else await loadSession(id);
    return;
  }
  go("home");
}

async function checkHealth() {
  const light = document.querySelector("#service-light");
  const status = document.querySelector("#service-status");
  try {
    await api("/api/health", {}, 5000);
    light.className = "service-light is-up";
    status.textContent = t("serviceUp");
  } catch {
    light.className = "service-light is-down";
    status.textContent = t("serviceDown");
  }
}

document.querySelectorAll("[data-route]").forEach((button) => {
  button.addEventListener("click", () => go(button.dataset.route));
});

document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", async () => {
    const form = document.querySelector("#story-form");
    if (form) state.teacherDraft = buildSpec(form).payload;
    state.lang = button.dataset.language;
    if (state.teacherDraft) state.teacherDraft.interface_language = state.lang;
    localStorage.setItem("pathlex.language", state.lang);
    if (state.session?.id) {
      try {
        state.session = unwrap(await api(`/api/sessions/${encodeURIComponent(state.session.id)}/language`, {
          method: "POST",
          body: JSON.stringify({ interface_language: state.lang }),
        }, 30000), "session");
      } catch (error) {
        toast(error.message || t("apiError"), "error");
      }
    }
    renderRoute();
    checkHealth();
  });
});

document.querySelector("#reset-language")?.addEventListener("click", async () => {
  localStorage.removeItem("pathlex.language");
  state.lang = "en";
  if (state.session?.id) {
    try {
      state.session = unwrap(await api(`/api/sessions/${encodeURIComponent(state.session.id)}/language`, {
        method: "POST",
        body: JSON.stringify({ interface_language: "en" }),
      }, 30000), "session");
    } catch (error) {
      toast(error.message || t("apiError"), "error");
    }
  }
  renderRoute();
  checkHealth();
  toast(t("languageResetToast"));
});

window.addEventListener("hashchange", renderRoute);
updateStaticLanguage();
renderRoute();
checkHealth();
