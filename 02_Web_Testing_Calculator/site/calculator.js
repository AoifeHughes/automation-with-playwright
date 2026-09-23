// The calculator's state machine, wired to the buttons on the page.
//
// State:
//   current           - the number being typed, as a string (starts at "0")
//   previous          - the left-hand operand of the pending operation (or null)
//   operator          - the pending operator: "+", "-", "×" or "÷" (or null)
//   waitingForOperand - true right after pressing an operator or "="

let current = "0";
let previous = null;
let operator = null;
let waitingForOperand = false;

const display = document.querySelector('[data-testid="display"]');

// What each operator button's data-testid maps to in the state machine.
// The minus button shows a proper minus sign, but the state uses "-".
const OPERATORS = {
  "op-plus": "+",
  "op-minus": "-",
  "op-multiply": "×",
  "op-divide": "÷",
};

function setDisplay(value) {
  display.textContent = String(value);
}

function compute(a, b, op) {
  if (op === "+") return a + b;
  if (op === "-") return a - b;
  if (op === "×") return a * b;
  if (op === "÷") return a / b;
  throw new Error(`Unknown operator: ${op}`);
}

function inputDigit(d) {
  if (waitingForOperand) {
    current = d;
    waitingForOperand = false;
  } else {
    current = current === "0" ? d : current + d;
  }
  setDisplay(current);
}

function chooseOperator(op) {
  if (operator !== null && !waitingForOperand) {
    // Chained operations: 2 + 3 + first becomes 5 + ...
    const intermediate = compute(previous, parseFloat(current), operator);
    previous = intermediate;
    setDisplay(intermediate);
  } else {
    previous = parseFloat(current);
  }
  operator = op;
  waitingForOperand = true;
}

function equals() {
  if (operator !== null) {
    const result = compute(previous, parseFloat(current), operator);
    current = String(result);
    previous = null;
    operator = null;
    waitingForOperand = true;
    setDisplay(result);
  }
}

function clear() {
  current = "0";
  previous = null;
  operator = null;
  waitingForOperand = false;
  setDisplay("0");
}

// Wire every button up through its data-testid.
document.querySelectorAll("button[data-testid]").forEach((button) => {
  button.addEventListener("click", () => {
    const testId = button.dataset.testid;
    if (testId.startsWith("digit-")) {
      inputDigit(testId.slice("digit-".length));
    } else if (testId in OPERATORS) {
      chooseOperator(OPERATORS[testId]);
    } else if (testId === "equals") {
      equals();
    } else if (testId === "clear") {
      clear();
    }
  });
});
