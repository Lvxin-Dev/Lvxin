document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const phoneForm = document.getElementById('phone-signup-form');
    const phoneInput = document.getElementById('phone-number');
    const sendCodeBtn = document.getElementById('send-code-btn');
    const otpSection = document.getElementById('otp-section');
    const otpInputs = document.querySelectorAll('.otp-input');
    const phoneFeedback = document.getElementById('phone-feedback');
    const otpFeedback = document.getElementById('otp-feedback');

    // --- State ---
    let state = {
        isSendingCode: false,
        isSigningUp: false,
        countdown: 0,
        formattedPhoneNumber: ''
    };

    // --- Utility Modules ---

    const ValidationUtils = {
        isValidPhoneNumber(phone) {
            try {
                const phoneNumber = libphonenumber.parsePhoneNumberFromString(phone);
                return phoneNumber && phoneNumber.isValid();
            } catch (error) {
                return false;
            }
        },
        formatPhoneNumber(phone) {
            try {
                const phoneNumber = libphonenumber.parsePhoneNumberFromString(phone);
                return phoneNumber ? phoneNumber.number : null;
            } catch (error) {
                return null;
            }
        },
        getOtp() {
            let otp = '';
            otpInputs.forEach(input => {
                otp += input.value;
            });
            return otp;
        }
    };

    const ApiUtils = {
        async sendVerificationCode(phone) {
            const formData = new FormData();
            formData.append('phone', phone);
            const response = await fetch('/auth/send-verification-code', {
                method: 'POST',
                body: formData
            });
            return response;
        },
        async signupByPhone(formData) {
            const response = await fetch('/auth/signup-by-phone', {
                method: 'POST',
                body: formData
            });
            return response;
        }
    };

    const UIUtils = {
        setLoading(button, isLoading) {
            button.disabled = isLoading;
            button.innerHTML = isLoading ? '<i class="fas fa-spinner fa-spin"></i>' : button.dataset.originalText;
        },
        setFeedback(element, message, isError = true) {
            element.textContent = message;
            element.className = 'feedback';
            if (message) {
                element.classList.add(isError ? 'error' : 'success');
            }
        },
        startCountdown() {
            state.countdown = 60;
            sendCodeBtn.disabled = true;
            const interval = setInterval(() => {
                state.countdown--;
                if (state.countdown > 0) {
                    sendCodeBtn.textContent = `Resend in ${state.countdown}s`;
                } else {
                    clearInterval(interval);
                    sendCodeBtn.textContent = 'Resend Code';
                    sendCodeBtn.disabled = false;
                }
            }, 1000);
        }
    };

    // --- Event Handlers ---

    async function handleSendCode() {
        UIUtils.setFeedback(phoneFeedback, '');
        const phone = phoneInput.value;

        if (!ValidationUtils.isValidPhoneNumber(phone)) {
            UIUtils.setFeedback(phoneFeedback, 'Invalid phone number format.');
            return;
        }

        state.formattedPhoneNumber = ValidationUtils.formatPhoneNumber(phone);
        if (!state.formattedPhoneNumber) {
             UIUtils.setFeedback(phoneFeedback, 'Could not format phone number.');
             return;
        }

        sendCodeBtn.dataset.originalText = sendCodeBtn.innerHTML;
        UIUtils.setLoading(sendCodeBtn, true);

        try {
            const response = await ApiUtils.sendVerificationCode(state.formattedPhoneNumber);
            if (response.ok) {
                UIUtils.setFeedback(phoneFeedback, 'Verification code sent!', false);
                otpSection.classList.remove('hidden');
                UIUtils.startCountdown();
            } else {
                const error = await response.json();
                UIUtils.setFeedback(phoneFeedback, error.detail || 'Failed to send code.');
            }
        } catch (error) {
            UIUtils.setFeedback(phoneFeedback, 'An unexpected error occurred.');
        } finally {
            UIUtils.setLoading(sendCodeBtn, false);
        }
    }

    async function handleSignup(e) {
        e.preventDefault();
        UIUtils.setFeedback(otpFeedback, '');
        
        const otp = ValidationUtils.getOtp();
        if (otp.length !== 6) {
            UIUtils.setFeedback(otpFeedback, 'Please enter the 6-digit code.');
            return;
        }

        const formData = new FormData(phoneForm);
        formData.append('code', otp);
        // Ensure phone number is in the correct format
        formData.set('phone', state.formattedPhoneNumber);
        
        const submitBtn = phoneForm.querySelector('button[type="submit"]');
        submitBtn.dataset.originalText = submitBtn.innerHTML;
        UIUtils.setLoading(submitBtn, true);
        
        try {
            const response = await ApiUtils.signupByPhone(formData);
            if(response.ok) {
                 UIUtils.setFeedback(otpFeedback, 'Signup successful! Redirecting...', false);
                 window.location.href = '/signin';
            } else {
                const error = await response.json();
                UIUtils.setFeedback(otpFeedback, error.detail || 'Signup failed.');
            }
        } catch (error) {
             UIUtils.setFeedback(otpFeedback, 'An unexpected error occurred.');
        } finally {
            UIUtils.setLoading(submitBtn, false);
        }
    }
    
    function handleOtpInput(e) {
        const currentInput = e.target;
        const nextInput = currentInput.nextElementSibling;
        const prevInput = currentInput.previousElementSibling;

        if (currentInput.value.length === 1 && nextInput) {
            nextInput.focus();
        }

        if (e.key === "Backspace" && !currentInput.value && prevInput) {
            prevInput.focus();
        }
    }
    
    function handleOtpPaste(e) {
        e.preventDefault();
        const pasteData = e.clipboardData.getData('text').slice(0, 6);
        otpInputs.forEach((input, index) => {
            input.value = pasteData[index] || '';
        });
        if(pasteData.length > 0) {
            const lastInputIndex = Math.min(pasteData.length, 6) - 1;
            otpInputs[lastInputIndex].focus();
        }
    }

    // --- Attach Event Listeners ---
    sendCodeBtn.addEventListener('click', handleSendCode);
    phoneForm.addEventListener('submit', handleSignup);
    otpInputs.forEach(input => {
        input.addEventListener('keyup', handleOtpInput);
        input.addEventListener('paste', handleOtpPaste);
    });
}); 