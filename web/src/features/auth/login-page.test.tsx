import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { LoginPage } from "./login-page";

describe("LoginPage", () => {
  it("submits the entered credentials", async () => {
    const user = userEvent.setup();
    const handleSubmit = vi.fn().mockResolvedValue(undefined);

    render(<LoginPage errorMessage={null} isSubmitting={false} onSubmit={handleSubmit} />);

    const usernameInput = screen.getByPlaceholderText("请输入用户名");
    const passwordInput = screen.getByPlaceholderText("请输入密码");
    await user.type(usernameInput, "editor");
    await user.type(passwordInput, "editor-secret");
    await user.click(screen.getByRole("button", { name: "登录" }));

    expect(handleSubmit).toHaveBeenCalledWith("editor", "editor-secret");
  });
});
