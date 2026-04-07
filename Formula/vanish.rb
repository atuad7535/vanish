class Vanish < Formula
  include Language::Python::Virtualenv

  desc "poof. your dev junk vanished. Smart cleanup for developers."
  homepage "https://github.com/atuad7535/vanish"
  url "https://files.pythonhosted.org/packages/source/v/vanish/vanish-1.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.12"

  resource "typer" do
    url "https://files.pythonhosted.org/packages/source/t/typer/typer-0.15.3.tar.gz"
    sha256 "PLACEHOLDER"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.9.4.tar.gz"
    sha256 "PLACEHOLDER"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "vanish", shell_output("#{bin}/vanish --version")
  end
end
