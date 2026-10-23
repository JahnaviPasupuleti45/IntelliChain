import { fireEvent, render, screen } from "@testing-library/react";
import App from "./App";

beforeEach(() => localStorage.clear());

test("shows the home page", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: /IntelliChain/i })).toBeInTheDocument();
});

test("protected pages send logged-out users to login", () => {
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /get started/i }));
  expect(screen.getByRole("heading", { name: /login/i })).toBeInTheDocument();
});

test("assistant answers render bold text instead of raw asterisks", async () => {
  localStorage.setItem("intellichain_token", "t");
  localStorage.setItem("intellichain_user", JSON.stringify({ fullname: "A", email: "a@b.c", phone: "1" }));
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ answer: "**SHP2** needs action\n* notify QA", sources: [], mode: "llm" }),
  });

  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: /ops copilot/i }));
  fireEvent.click(screen.getByRole("button", { name: /what should we do about shp2/i }));

  const bold = await screen.findByText("SHP2", { selector: "strong" });
  expect(bold).toBeInTheDocument();
  expect(screen.getByText(/• notify QA/)).toBeInTheDocument();
  expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument();
});

test("dashboard link is hidden until the user logs in", () => {
  render(<App />);
  expect(screen.queryByRole("button", { name: /dashboard/i })).not.toBeInTheDocument();
});
