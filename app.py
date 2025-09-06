# app.py
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from sympy import symbols, Eq, sympify, factor, solve, simplify, N, re, im
import uvicorn

app = FastAPI()


def parse_and_explain_system(expr_text: str, only_real: bool = True):
    steps_list = []
    expr_list = [line.strip() for line in expr_text.splitlines() if line.strip()]
    eqs = []
    all_vars = set()

    try:
        # Parse each equation
        for eq_str in expr_list:
            if "=" in eq_str:
                left, right = eq_str.split("=", 1)
                left_sym = sympify(left)
                right_sym = sympify(right)
                eq = Eq(left_sym, right_sym)
            else:
                expr = sympify(eq_str)
                eq = Eq(expr, 0)
            eqs.append(eq)
            all_vars.update(eq.free_symbols)

            # Step 1: Simplify
            simplified = simplify(eq.lhs - eq.rhs)
            if str(simplified) != str(eq.lhs - eq.rhs):
                steps_list.append({
                    "step": f"Simplified: {eq} → {simplified} = 0",
                    "hint": "We simplified the equation to make it easier to solve."
                })
                eqs[-1] = Eq(simplified, 0)

            # Step 2: Factor
            factored = factor(simplified)
            if str(factored) != str(simplified):
                steps_list.append({
                    "step": f"Factored: {simplified} → {factored} = 0",
                    "hint": "We factored the expression to find the roots more easily."
                })
                eqs[-1] = Eq(factored, 0)

        all_vars = list(all_vars)

        # Step 3: Solve
        sols_raw = solve(eqs, all_vars, dict=True)

        solution_blocks = []
        if sols_raw:
            for idx, sol in enumerate(sols_raw, start=1):
                block = [f"<b>Solution {idx}:</b>"]
                for var in all_vars:
                    val = sol.get(var, '__')
                    # Only show real part if selected
                    if only_real and val.is_complex:
                        if im(val) != 0:
                            val_display = "__"
                        else:
                            val_display = N(re(val), 4)
                    else:
                        val_display = N(val, 4) if val != '__' else '__'
                    block.append(f"{var} = {val_display}")
                solution_blocks.append("<br>".join(block))
        else:
            solution_blocks = [f"{v} = __" for v in all_vars]

        solution_text = "<br><br>".join(solution_blocks)

        # Ensure hints are always shown
        if not steps_list:
            steps_list.append({
                "step": "No intermediate steps available",
                "hint": "This equation is already simple or cannot be factored further."
            })

        return steps_list, solution_text

    except Exception as e:
        return [{"step": f"Error: {str(e)}", "hint": ""}], "<br>".join([f"{v} = __" for v in all_vars]) if all_vars else "No solutions found."


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
      <body style="font-family: sans-serif; padding: 20px;">
        <h1>AI Personal Math Tutor</h1>
        <p>Tip: Use <b>*</b> for multiplication and <b>**</b> for exponents.<br>
        Example: x**2 means x squared, and 2*x means 2 times x.</p>
        <p>Example input (one equation per line):<br>
        x + y = 0<br>
        x - 2*y = 4</p>
        <form action="/solve" method="post">
          <label>Enter your equations (one per line):</label><br>
          <textarea name="exprs" rows="5" cols="50"></textarea><br><br>
          <input type="checkbox" name="only_real" checked> Show only real solutions<br><br>
          <button type="submit" name="action" value="hint">Show Hint</button>
          <button type="submit" name="action" value="answer">Show Answer</button>
        </form>
      </body>
    </html>
    """


@app.post("/solve", response_class=HTMLResponse)
async def solve_endpoint(exprs: str = Form(...), action: str = Form(...), only_real: str = Form("on")):
    show_real_only = True if only_real == "on" else False
    steps, solution_text = parse_and_explain_system(exprs, only_real=show_real_only)

    if action == "hint":
        steps_html = ""
        for s in steps:
            steps_html += f"<b>{s['step']}</b><br><i>Hint: {s['hint']}</i><br><br>"

        return f"""
        <html>
          <body style="font-family: sans-serif; padding: 20px;">
            <h1>Hints</h1>
            <p>{steps_html}</p>
            <form action="/solve" method="post">
                <input type="hidden" name="exprs" value='{exprs.replace("'", "&apos;").replace("\n", "&#10;")}'>
                <input type="hidden" name="only_real" value='{"on" if show_real_only else "off"}'>
                <button type="submit" name="action" value="answer">Show Answer</button>
            </form>
            <a href="/">Try another system</a>
          </body>
        </html>
        """
    else:
        return f"""
        <html>
          <body style="font-family: sans-serif; padding: 20px;">
            <h1>Solutions</h1>
            <p>{solution_text}</p>
            <button onclick="copySolutions()">Copy Solutions</button>
            <script>
                function copySolutions(){{
                    const el = document.createElement('textarea');
                    el.value = `{solution_text.replace('<br>', '\\n')}`;
                    document.body.appendChild(el);
                    el.select();
                    document.execCommand('copy');
                    document.body.removeChild(el);
                    alert('Solutions copied!');
                }}
            </script>
            <a href="/">Try another system</a>
          </body>
        </html>
        """


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
