package com.achen.novelbridge.pojo.vo;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Evaluation case view object returned by eval case endpoints.
 * <p>
 * expectedEntities is parsed from the JSON string stored in the entity.
 * </p>
 */
public class EvalCaseVO {

    private Long id;
    private Long bookId;
    private String question;
    private String expectedAnswer;
    private List<String> expectedEntities;
    private String category;
    private String difficulty;
    private String status;
    private LocalDateTime createdAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getBookId() {
        return bookId;
    }

    public void setBookId(Long bookId) {
        this.bookId = bookId;
    }

    public String getQuestion() {
        return question;
    }

    public void setQuestion(String question) {
        this.question = question;
    }

    public String getExpectedAnswer() {
        return expectedAnswer;
    }

    public void setExpectedAnswer(String expectedAnswer) {
        this.expectedAnswer = expectedAnswer;
    }

    public List<String> getExpectedEntities() {
        return expectedEntities;
    }

    public void setExpectedEntities(List<String> expectedEntities) {
        this.expectedEntities = expectedEntities;
    }

    public String getCategory() {
        return category;
    }

    public void setCategory(String category) {
        this.category = category;
    }

    public String getDifficulty() {
        return difficulty;
    }

    public void setDifficulty(String difficulty) {
        this.difficulty = difficulty;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }
}
