from jev_lab.model_router.router import eligible_models, routing_criteria, routing_question


def test_all_six_models_are_available_to_the_unconstrained_router():
    assert set(eligible_models()) == {"luna", "terra", "sol", "haiku", "sonnet", "opus"}
    assert set(routing_criteria()) == {"luna", "terra", "sol", "haiku", "sonnet", "opus"}


def test_provider_filter_limits_choice_options():
    assert set(routing_criteria("openai")) == {"luna", "terra", "sol"}
    assert set(routing_criteria("anthropic")) == {"haiku", "sonnet", "opus"}
    assert routing_question("openai").criteria["luna"]


def test_batch_router_accepts_per_task_provider_constraints():
    from jev_lab.model_router.router import route_questions

    questions = route_questions(["cheap task", "complex task"], ["openai", "anthropic"])
    assert set(questions["task_1"].criteria) == {"luna", "terra", "sol"}
    assert set(questions["task_2"].criteria) == {"haiku", "sonnet", "opus"}
